import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from physics_ai_tutor.core import prompts
from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.exceptions import ConceptExtractionError
from physics_ai_tutor.models import Concept
from physics_ai_tutor.repositories import (
    concept_repository,
    question_concept_repository,
)
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.services import deepseek_service, embedding_service

logger = logging.getLogger(__name__)

CONCEPT_EXTRACTION_PROMPT_VERSION = "v2"

_SYSTEM_PROMPT = (
    "You are an expert in physics education. Your output is processed "
    "automatically: print only the required format, one concept per line as "
    "'<Japanese name> | <English name>', and nothing else."
)

_USER_PROMPT_TEMPLATE = """---Example---

Question:
加速度って何?

Answer:
加速度は単位時間あたりの速度の変化量です。
速度と同じくベクトル量で、単位は $m/s^2$ です。

速度-時間グラフの接線の傾きを考えると、加速度になります。

Output:
加速度 | acceleration
単位時間 | unit time
速度 | velocity
変化量 | change
ベクトル | vector
単位 | unit
$m/s^2$ | $m/s^2$
v-tグラフ | v-t graph
接線の傾き | slope of the tangent
微分 | differentiation
---End of example---
As in the example, extract the physics concepts from the following question
and answer (written in {language_name}). Print one concept per line as
'<Japanese name> | <English name>', newline separated, and nothing else.
{glossary}
Question:
{question}

Answer:
{answer}

Output:
"""


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
    user_prompt = _USER_PROMPT_TEMPLATE.format(
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
