import logging
import re
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.core import prompts
from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.exceptions import ConceptExtractionError, TranslationError
from physics_ai_tutor.core.prompt_library import load_library
from physics_ai_tutor.core.text import concept_pair_text, normalize_key
from physics_ai_tutor.database.transaction import transaction
from physics_ai_tutor.models import Concept
from physics_ai_tutor.repositories import (
    concept_repository,
    concept_term_repository,
    question_concept_repository,
)
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.services import (
    concept_sense_service,
    deepseek_service,
    embedding_service,
    translation_service,
)

logger = logging.getLogger(__name__)

_LIBRARY = load_library()

CONCEPT_EXTRACTION_PROMPT_VERSION = _LIBRARY.version("concept_extraction")

_SYSTEM_PROMPT = _LIBRARY.get("concept_extraction", "system")
_USER_PROMPT_TEMPLATE = _LIBRARY.get("concept_extraction", "user_template")


@dataclass(frozen=True)
class ConceptName:
    ja: str | None
    en: str | None

    def primary(self, language: str) -> str:
        name = self.ja if language == "ja" else self.en
        if name is None:
            name = self.en if language == "ja" else self.ja
        assert name is not None
        return name


# Two-axis difficulty ([40]), 0-4, rated by the nature of the content
# itself rather than a school curriculum (owner's policy, 2026-11-01).
# One rating per QA pair: what a reader needs to follow it (2026-11-04).
MAX_LEVEL = 4

_LEVELS_LINE = re.compile(
    r"^levels:\s*physics\s*=\s*(\d+)\s+math\s*=\s*(\d+)\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExtractionLevels:
    physics: int
    math: int


def parse_levels_line(line: str) -> ExtractionLevels | None:
    """Parse 'LEVELS: physics=N math=N'."""
    match = _LEVELS_LINE.match(line.strip())
    if match is None:
        return None

    # The scale is ordinal; an overshoot means "at least the top level".
    values = [min(int(group), MAX_LEVEL) for group in match.groups()]

    return ExtractionLevels(*values)


def find_levels(lines: list[str]) -> ExtractionLevels | None:
    """The levels line from raw extraction output; None when absent/garbled."""
    for line in lines:
        levels = parse_levels_line(line)
        if levels is not None:
            return levels
    return None


def apply_levels_to_question(question, lines: list[str]) -> None:
    """Store the LLM's advisory ratings; a teacher may overwrite them later."""
    levels = find_levels(lines)
    if levels is None:
        logger.info(
            "Concept extraction carried no levels line: question_id=%s", question.id
        )
        return

    question.physics_level = levels.physics
    question.math_level = levels.math


def parse_concept_line(line: str, language: str = "ja") -> ConceptName | None:
    """Parse '<ja> | <en>'. A bare name is assigned to `language`."""
    line = line.strip()
    if not line:
        return None

    # The levels line also contains '|'; it is metadata, not a concept.
    if parse_levels_line(line) is not None:
        return None

    if "|" in line:
        ja, en = (part.strip() or None for part in line.split("|", 1))
        if ja is None and en is None:
            return None
        return ConceptName(ja=ja, en=en)

    return (
        ConceptName(ja=line, en=None)
        if language == "ja"
        else ConceptName(ja=None, en=line)
    )


def _user_prompt(question: str, answer: str, language: str) -> str:
    # The worked example matches the row's language: few-shot examples
    # steer the model more than the instruction text does.
    return _USER_PROMPT_TEMPLATE.format(
        example=_LIBRARY.get("concept_extraction", "example", language),
        language_name=prompts.LANGUAGE_NAMES[Language(language)],
        glossary=prompts.glossary_block(),
        question=question,
        answer=answer,
    )


async def extract_concept_names(
    question: str, answer: str, language: str = "ja"
) -> list[str]:
    """As `extract_concept_names`, on the event loop ([91])."""
    content = await deepseek_service.chat_completion(
        _SYSTEM_PROMPT, _user_prompt(question, answer, language)
    )
    return _extracted_lines(content)


def _extracted_lines(content: str) -> list[str]:
    lines = [line.strip() for line in content.splitlines() if line.strip()]

    if not lines:
        logger.warning(
            "Concept extraction returned no concepts: content=%r", content[:500]
        )
        raise ConceptExtractionError(
            "DeepSeek returned no concepts for concept extraction."
        )

    logger.info("Concepts extracted: count=%d", len(lines))

    return lines


def _sense_pair_text(concept: Concept) -> str:
    return concept_pair_text(concept.name_ja, concept.name_en)


SenseIndex = dict[tuple[str, str], list[Concept]]


def _sides(name: ConceptName) -> list[tuple[str, str]]:
    return [(lang, word) for lang, word in (("ja", name.ja), ("en", name.en)) if word]


def _word_keys(name: ConceptName) -> set[tuple[str, str]]:
    return {(lang, normalize_key(word)) for lang, word in _sides(name)}


# Words planned for a sense but not written yet: (id(concept), lang, key).
Pending = set[tuple[int, str, str]]


def _has(concept: Concept, language: str, word: str, pending: Pending) -> bool:
    if concept_sense_service.has_term(concept, language, word):
        return True
    return (id(concept), language, normalize_key(word)) in pending


def _candidates(
    index: SenseIndex, name: ConceptName, pending: Pending
) -> tuple[list[Concept], list[Concept]]:
    """(senses having both words, senses to compare); both empty = new sense.

    Keyed by object identity, so a sense planned but not saved yet (no id)
    can match a later pair of the same question ([91]).
    """
    candidates: dict[int, Concept] = {}
    for key in _word_keys(name):
        for concept in index.get(key, []):
            candidates[id(concept)] = concept
    full = [
        concept
        for concept in candidates.values()
        if all(_has(concept, lang, w, pending) for lang, w in _sides(name))
    ]
    return full, full or list(candidates.values())


def _pair_texts(name: ConceptName, pool: list[Concept]) -> list[str]:
    return [concept_pair_text(name.ja, name.en), *(_sense_pair_text(c) for c in pool)]


async def _resolve_sense(
    index: SenseIndex, name: ConceptName, pending: Pending
) -> tuple[Concept | None, list[float] | None]:
    """As `_resolve_sense`; the embedding call runs with no session in use."""
    full, pool = _candidates(index, name, pending)
    if not pool:
        return None, None
    if len(full) == 1:
        return full[0], None
    vectors = await embedding_service.create_embeddings(_pair_texts(name, pool))
    return _choose(name, full, pool, vectors)


def _choose(
    name: ConceptName,
    full: list[Concept],
    pool: list[Concept],
    vectors: list[list[float]],
) -> tuple[Concept | None, list[float]]:
    """The closest sense by pair embedding, or None below the threshold."""
    mine, others = vectors[0], vectors[1:]
    scored = sorted(
        zip((concept_sense_service.cosine(mine, v) for v in others), pool, strict=True),
        key=lambda item: item[0],
        reverse=True,
    )
    best_score, best = scored[0]
    if full or best_score >= settings.concept_sense_match_threshold:
        return best, mine
    logger.info(
        "New concept sense for a shared word: pair=%r best=%.3f",
        concept_pair_text(name.ja, name.en),
        best_score,
    )
    return None, mine


def _parse_names(concept_names: list[str], language: str) -> list[ConceptName]:
    """Parsed pairs, duplicates dropped, order kept."""
    names: list[ConceptName] = []
    seen: set[tuple[str | None, str | None]] = set()
    for raw in concept_names:
        name = parse_concept_line(raw, language)
        if name is not None and (name.ja, name.en) not in seen:
            seen.add((name.ja, name.en))
            names.append(name)
    return names


def _all_keys(names: list[ConceptName]) -> set[tuple[str, str]]:
    return set().union(*(_word_keys(name) for name in names)) if names else set()


@dataclass
class PlannedSense:
    """One sense an extraction resolved to, before anything is written."""

    concept: Concept
    new: bool
    # Words to add to an existing sense when the plan is applied.
    aliases: list[tuple[str, str]]


async def prepare_concepts(
    db: AsyncSession, concept_names: list[str], language: str
) -> list[PlannedSense]:
    """Resolve extracted pairs to senses without writing ([91]).

    The index is read in its own short transaction; any embedding call
    happens after it, so no connection waits on OpenAI ([82]).
    """
    return (await prepare_concepts_many(db, [(concept_names, language)]))[0]


async def prepare_concepts_many(
    db: AsyncSession, items: list[tuple[list[str], str]]
) -> list[list[PlannedSense]]:
    """`prepare_concepts` for several questions sharing one index ([94]).

    The index is read once for every pair of every question, and a sense
    planned for one question can be matched by a later one, so an import
    never creates the same new sense twice.
    """
    parsed = [_parse_names(names, language) for names, language in items]
    keys = set().union(*(_all_keys(names) for names in parsed)) if parsed else set()
    async with transaction(db, "concept_index_read"):
        index = await concept_term_repository.senses_by_words(db, keys)
    return [await _plan(index, names) for names in parsed]


async def _plan(index: SenseIndex, names: list[ConceptName]) -> list[PlannedSense]:
    pending: Pending = set()
    plans: dict[int, PlannedSense] = {}
    for name in names:
        concept, embedding = await _resolve_sense(index, name, pending)
        if concept is None:
            concept = await _build_sense(name, embedding)
            plans[id(concept)] = PlannedSense(concept, new=True, aliases=[])
            # Later pairs of this question may share a word with it.
            for key in _word_keys(name):
                index.setdefault(key, []).append(concept)
            continue
        plan = plans.setdefault(
            id(concept), PlannedSense(concept, new=False, aliases=[])
        )
        for lang, word in _sides(name):
            if plan.new:
                # An unsaved sense takes its alias straight away.
                concept_sense_service.add_unsaved_term(
                    concept, lang, word, concept_sense_service.TermSource.EXTRACTED
                )
            elif not _has(concept, lang, word, pending):
                pending.add((id(concept), lang, normalize_key(word)))
                plan.aliases.append((lang, word))
    return list(plans.values())


async def _build_sense(name: ConceptName, embedding: list[float] | None) -> Concept:
    if embedding is None:
        embedding = (
            await embedding_service.create_embeddings(
                [concept_pair_text(name.ja, name.en)]
            )
        )[0]
    return concept_repository.build(
        embedding=embedding,
        extraction_model=settings.deepseek_chat_model,
        embedding_model=settings.embedding_model,
        extraction_prompt_version=CONCEPT_EXTRACTION_PROMPT_VERSION,
        name_ja=name.ja,
        name_en=name.en,
    )


async def attach_concepts(
    db: AsyncSession, question_id: int, concept_names: list[str], language: str = "ja"
) -> list[Concept]:
    """Prepare and apply for one question: plan, then one short write ([95])."""
    plans = await prepare_concepts(db, concept_names, language)
    async with transaction(db, "attach_concepts"):
        return await apply_concepts(db, question_id, plans)


async def apply_concepts(
    db: AsyncSession, question_id: int, plans: list[PlannedSense]
) -> list[Concept]:
    """Write a plan from `prepare_concepts`; call inside a transaction."""
    for plan in plans:
        if plan.new:
            db.add(plan.concept)
    await db.flush()
    for plan in plans:
        for lang, word in plan.aliases:
            await concept_sense_service.add_term(
                db,
                plan.concept,
                lang,
                word,
                concept_sense_service.TermSource.EXTRACTED,
            )
    concepts = [plan.concept for plan in plans]
    await question_concept_repository.link_many(
        db, question_id, [concept.id for concept in concepts]
    )
    return concepts


def _missing_and_present(concept: Concept) -> tuple[list[str], list[str]]:
    missing = [
        lang
        for lang in ("ja", "en")
        if concept_sense_service.preferred_term(concept, lang) is None
    ]
    present = [lang for lang in ("ja", "en") if lang not in missing]
    return missing, present


async def translate_missing_name(db: AsyncSession, concept_id: int) -> bool:
    """As `translate_missing_name`, on the event loop ([72])."""
    async with transaction(db, "concept_name_read"):
        concept = await db.get(Concept, concept_id)
        if concept is None:
            plan = None
        else:
            missing, present = _missing_and_present(concept)
            if not missing or not present:
                plan = None
            else:
                source, target = Language(present[0]), Language(missing[0])
                word = concept_sense_service.preferred_term(concept, source.value)
                assert word is not None
                context = await question_concept_repository.context_question(
                    db, concept_id, source.value
                )
                plan = (source, target, word.term, context)

    if plan is None or concept is None:
        return False

    source, target, word_text, context = plan

    try:
        translated, _ = await translation_service.translate_qa(
            word_text, context or word_text, source, target
        )
    except TranslationError:
        logger.warning("Concept name translation failed: concept_id=%d", concept_id)
        return False

    async with transaction(db, "translate_concept_name"):
        added = await concept_sense_service.add_term(
            db,
            concept,
            target.value,
            translated,
            concept_sense_service.TermSource.MACHINE,
        )
    return added is not None
