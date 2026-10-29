import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from physics_ai_tutor.core import prompts
from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.exceptions import ConceptExtractionError
from physics_ai_tutor.core.prompt_library import load_library
from physics_ai_tutor.models import Concept
from physics_ai_tutor.repositories import (
    concept_repository,
    question_concept_repository,
)
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.services import deepseek_service, embedding_service

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


def parse_concept_line(line: str, language: str = "ja") -> ConceptName | None:
    """Parse '<ja> | <en>'. A bare name is assigned to `language`."""
    line = line.strip()
    if not line:
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


def _find_existing(db: Session, name: ConceptName) -> Concept | None:
    if name.ja is not None:
        found = concept_repository.get_by_name(db, name.ja, language="ja")
        if found is not None:
            return found
    if name.en is not None:
        return concept_repository.get_by_name(db, name.en, language="en")
    return None


def attach_concepts_to_question(
    db: Session,
    question_id: int,
    concept_names: list[str],
    language: str = "ja",
) -> list[Concept]:
    concepts = []
    seen: set[tuple[str | None, str | None]] = set()

    for raw in concept_names:
        name = parse_concept_line(raw, language)
        if name is None or (name.ja, name.en) in seen:
            continue
        seen.add((name.ja, name.en))

        concept = _find_existing(db, name)

        if concept is None:
            embedding = embedding_service.create_embeddings([name.primary(language)])[0]
            concept = concept_repository.create(
                db,
                name_ja=name.ja,
                name_en=name.en,
                embedding=embedding,
                extraction_model=settings.deepseek_chat_model,
                embedding_model=settings.embedding_model,
                extraction_prompt_version=CONCEPT_EXTRACTION_PROMPT_VERSION,
            )
        else:
            # Fill in a missing translation of a known concept.
            if concept.name_ja is None and name.ja is not None:
                concept.name_ja = name.ja
            if concept.name_en is None and name.en is not None:
                concept.name_en = name.en
            db.flush()

        question_concept_repository.link(
            db, question_id=question_id, concept_id=concept.id
        )
        concepts.append(concept)

    return concepts
