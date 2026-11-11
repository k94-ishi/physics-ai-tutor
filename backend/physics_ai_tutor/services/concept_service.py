import logging
import re
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from physics_ai_tutor.core import prompts
from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.exceptions import ConceptExtractionError, TranslationError
from physics_ai_tutor.core.prompt_library import load_library
from physics_ai_tutor.core.text import concept_pair_text, normalize_key
from physics_ai_tutor.database.transaction import async_transaction, transaction
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


def extract_concept_names(
    question: str, answer: str, language: str = "ja"
) -> list[str]:
    """Return raw '<ja> | <en>' lines from the model (parsed later)."""
    # The worked example matches the row's language: few-shot examples
    # steer the model more than the instruction text does.
    user_prompt = _USER_PROMPT_TEMPLATE.format(
        example=_LIBRARY.get("concept_extraction", "example", language),
        language_name=prompts.LANGUAGE_NAMES[Language(language)],
        glossary=prompts.glossary_block(),
        question=question,
        answer=answer,
    )

    content = deepseek_service.chat_completion(_SYSTEM_PROMPT, user_prompt)

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


def _resolve_sense(
    index: SenseIndex, name: ConceptName
) -> tuple[Concept | None, list[float] | None]:
    """The existing sense this pair means, or None (+ its embedding if computed).

    Both words known on one sense -> that sense. A sense sharing only one
    word is a synonym or a homonym (速度 = velocity / speed, 位相 = phase /
    topology): decided by embedding similarity of the two pairs ([55]).
    """
    sides = _sides(name)
    candidates: dict[int, Concept] = {}
    for key in _word_keys(name):
        for concept in index.get(key, []):
            candidates[concept.id] = concept
    if not candidates:
        return None, None

    full = [
        concept
        for concept in candidates.values()
        if all(concept_sense_service.has_term(concept, lang, w) for lang, w in sides)
    ]
    if len(full) == 1:
        return full[0], None

    pool = full or list(candidates.values())
    vectors = embedding_service.create_embeddings(
        [concept_pair_text(name.ja, name.en), *(_sense_pair_text(c) for c in pool)]
    )
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


def _new_sense(
    name: ConceptName, embedding: list[float] | None, db: Session
) -> Concept:
    """Create a sense with its words in one insert (no follow-up UPDATE)."""
    if embedding is None:
        embedding = embedding_service.create_embeddings(
            [concept_pair_text(name.ja, name.en)]
        )[0]
    return concept_repository.create(
        db,
        embedding=embedding,
        extraction_model=settings.deepseek_chat_model,
        embedding_model=settings.embedding_model,
        extraction_prompt_version=CONCEPT_EXTRACTION_PROMPT_VERSION,
        name_ja=name.ja,
        name_en=name.en,
    )


def attach_concepts_to_question(
    db: Session,
    question_id: int,
    concept_names: list[str],
    language: str = "ja",
) -> list[Concept]:
    """Resolve each `<ja> | <en>` line to a sense and link it to the question.

    All words of the question are looked up at once and the links are
    written together, so the cost per question is a handful of queries
    rather than several per concept ([66]).
    """
    names: list[ConceptName] = []
    seen: set[tuple[str | None, str | None]] = set()
    for raw in concept_names:
        name = parse_concept_line(raw, language)
        if name is not None and (name.ja, name.en) not in seen:
            seen.add((name.ja, name.en))
            names.append(name)

    index = concept_term_repository.senses_by_words(
        db, set().union(*(_word_keys(name) for name in names)) if names else set()
    )
    concepts: list[Concept] = []
    for name in names:
        concept, embedding = _resolve_sense(index, name)
        if concept is None:
            concept = _new_sense(name, embedding, db)
            # Later pairs of this question may share a word with it.
            for key in _word_keys(name):
                index.setdefault(key, []).append(concept)
        else:
            # New words of a known sense become aliases.
            for lang, word in _sides(name):
                concept_sense_service.add_term(
                    db, concept, lang, word, concept_sense_service.TermSource.EXTRACTED
                )
        if concept not in concepts:
            concepts.append(concept)

    question_concept_repository.link_many(
        db, question_id, [concept.id for concept in concepts]
    )
    return concepts


def translate_missing_name(db: Session, concept_id: int) -> bool:
    """Add a machine term for a language the sense has no word in; commits.

    Reuses `translation_service.translate_qa` with the word as the question
    and a QA that uses it as the answer, so the translator sees the context
    that separates 位相 (phase) from 位相 (topology). No new prompt ([53]).
    """
    # The reads commit before the LLM call, so no connection waits ([82]).
    with transaction(db, "concept_name_read"):
        plan = _name_translation_plan(db, concept_id)

    if plan is None:
        return False

    concept, source, target, word, context = plan

    try:
        translated, _ = translation_service.translate_qa(
            word, context or word, source, target
        )
    except TranslationError:
        logger.warning("Concept name translation failed: concept_id=%d", concept_id)
        return False

    with transaction(db, "translate_concept_name"):
        added = concept_sense_service.add_term(
            db,
            concept,
            target.value,
            translated,
            concept_sense_service.TermSource.MACHINE,
        )
    return added is not None


def _missing_and_present(concept: Concept) -> tuple[list[str], list[str]]:
    missing = [
        lang
        for lang in ("ja", "en")
        if concept_sense_service.preferred_term(concept, lang) is None
    ]
    present = [lang for lang in ("ja", "en") if lang not in missing]
    return missing, present


def _name_translation_plan(db: Session, concept_id: int):
    """What to translate for this sense, or None when there is nothing."""
    concept = db.get(Concept, concept_id)
    if concept is None:
        return None

    missing, present = _missing_and_present(concept)
    if not missing or not present:
        return None

    source, target = Language(present[0]), Language(missing[0])
    word = concept_sense_service.preferred_term(concept, source.value)
    assert word is not None
    context = question_concept_repository.context_question(db, concept_id, source.value)

    return concept, source, target, word.term, context


async def async_translate_missing_name(db: AsyncSession, concept_id: int) -> bool:
    """As `translate_missing_name`, on the event loop ([72])."""
    async with async_transaction(db, "concept_name_read"):
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
                context = await question_concept_repository.async_context_question(
                    db, concept_id, source.value
                )
                plan = (source, target, word.term, context)

    if plan is None or concept is None:
        return False

    source, target, word_text, context = plan

    try:
        translated, _ = await translation_service.async_translate_qa(
            word_text, context or word_text, source, target
        )
    except TranslationError:
        logger.warning("Concept name translation failed: concept_id=%d", concept_id)
        return False

    async with async_transaction(db, "translate_concept_name"):
        added = await concept_sense_service.async_add_term(
            db,
            concept,
            target.value,
            translated,
            concept_sense_service.TermSource.MACHINE,
        )
    return added is not None
