"""Prerequisites for a QA: "what should I read first?" ([38]).

Distinct from the similarity-based related list: for each concept the
current QA leans on, offer the APPROVED QA that *defines* it at a level
the asker can climb down to. Concepts with no such QA are returned as
gaps so the UI can show them honestly instead of dropping them. No LLM
or embedding calls: concepts and levels are already on the rows.
"""

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.models.concept import Concept
from physics_ai_tutor.models.question import Question
from physics_ai_tutor.repositories import (
    question_concept_repository,
    question_repository,
)
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.question import (
    PrerequisitesResponse,
    QuestionResponse,
)
from physics_ai_tutor.services.question_presentation_service import (
    async_prepare_for_response,
)
from physics_ai_tutor.services.response_language import (
    ResponseLanguage,
    TranslationNeeds,
)

logger = logging.getLogger(__name__)


@dataclass
class Prerequisites:
    response: PrerequisitesResponse
    # Rows and concept names a strict reader missed ([53]).
    needs: TranslationNeeds


# A question "defines" a concept when it reads like a definition request.
_DEFINITION_MARKERS_JA = ("とは", "ってなに", "って何", "とはなに", "とは何")
_DEFINITION_MARKERS_EN = ("what is", "what are", "what does")


def _is_definition_question(text: str | None, concept_name: str | None) -> bool:
    """The question mentions the concept and asks what it is."""
    if not text or not concept_name:
        return False

    lowered = text.lower()
    if concept_name.lower() not in lowered:
        return False

    return any(marker in lowered for marker in _DEFINITION_MARKERS_JA) or any(
        marker in lowered for marker in _DEFINITION_MARKERS_EN
    )


def _defines(question: Question, concept: Concept) -> bool:
    # Any word of the sense counts: 速度 is defined by "what is velocity?" too ([55]).
    return any(
        _is_definition_question(question.question_ja, term.term)
        for term in concept.terms_in("ja")
    ) or any(
        _is_definition_question(question.question_en, term.term)
        for term in concept.terms_in("en")
    )


def _not_more_advanced(candidate: Question, current: Question) -> bool:
    """Never offer a climb *up*: unknown levels pass, higher levels do not."""
    for axis in ("physics_level", "math_level"):
        candidate_level = getattr(candidate, axis)
        current_level = getattr(current, axis)
        if (
            candidate_level is not None
            and current_level is not None
            and candidate_level > current_level
        ):
            return False
    return True


def _stuck_axis(current: Question) -> str:
    """The axis the asker most likely needs help with: the higher one."""
    physics = current.physics_level or 0
    math = current.math_level or 0
    return "math_level" if math > physics else "physics_level"


def _rank(question: Question) -> tuple[int, int]:
    return ((question.physics_level or 0) + (question.math_level or 0), question.id)


Link = tuple[Concept, Question]


def _readable_only(
    links: list[Link], response: ResponseLanguage
) -> tuple[list[Link], list[int]]:
    """Drop definers a strict reader cannot read; they are not definers yet."""
    readable, missing = response.readable(
        list({candidate.id: candidate for _, candidate in links}.values())
    )
    readable_ids = {question.id for question in readable}
    return [link for link in links if link[1].id in readable_ids], missing


def _best_definers(links: list[Link], current: Question) -> dict[int, Link]:
    """Per concept, the least advanced QA that defines it (ties: older row)."""
    best_by_concept: dict[int, Link] = {}
    for concept, candidate in links:
        if not _defines(candidate, concept):
            continue
        if not _not_more_advanced(candidate, current):
            continue
        best = best_by_concept.get(concept.id)
        if best is None or _rank(candidate) < _rank(best[1]):
            best_by_concept[concept.id] = (concept, candidate)
    return best_by_concept


async def _gaps(
    db: AsyncSession,
    question_id: int,
    covered: dict[int, Link],
    lang: Language,
    strict: bool,
) -> list[str]:
    """Names of this QA's concepts that ended up with no usable definer."""
    current_concepts = (
        await question_concept_repository.async_get_concepts_for_question(
            db, question_id
        )
    )
    return [
        name
        for concept in current_concepts
        if concept.id not in covered
        and (
            name := concept.name_in(lang.value)
            if strict
            else concept.display_name(lang.value)
        )
        is not None
    ]


def _hardest_first(
    best_by_concept: dict[int, Link], current: Question, limit: int
) -> list[Question]:
    """One card per QA; the hardest on the stuck axis is the next step down."""
    axis = _stuck_axis(current)
    unique: dict[int, Question] = {}
    for _, candidate in best_by_concept.values():
        unique[candidate.id] = candidate
    return sorted(
        unique.values(),
        key=lambda q: (getattr(q, axis) or 0, -q.id),
        reverse=True,
    )[:limit]


async def get_prerequisites(
    db: AsyncSession,
    question_id: int,
    limit: int = 5,
    language: Language | str | ResponseLanguage = Language.JA,
) -> Prerequisites | None:
    """Defining QAs for this QA's concepts, plus the concepts with none ([38])."""
    response = ResponseLanguage.of(language)
    lang = response.language
    current = await question_repository.async_get_question(db, question_id)
    if current is None:
        return None

    links = await question_concept_repository.approved_links_sharing_concepts(
        db, question_id
    )
    links, missing = _readable_only(links, response)
    best_by_concept = _best_definers(links, current)
    gaps = await _gaps(db, question_id, best_by_concept, lang, response.strict)
    ordered = _hardest_first(best_by_concept, current, limit)
    needs = await async_prepare_for_response(db, ordered, response)
    if response.strict:
        # The current QA's own concepts are the gap chips.
        needs.concept_question_ids.insert(0, question_id)

    logger.info(
        "Prerequisites computed: question_id=%d definers=%d gaps=%d",
        question_id,
        len(ordered),
        len(gaps),
    )
    return Prerequisites(
        response=PrerequisitesResponse(
            items=[QuestionResponse.model_validate(question) for question in ordered],
            gaps=gaps,
        ),
        needs=TranslationNeeds(question_ids=missing).merge(needs),
    )
