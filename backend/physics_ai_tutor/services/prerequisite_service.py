"""Prerequisites for a QA: "what should I read first?" ([38]).

Distinct from the similarity-based related list: for each concept the
current QA leans on, offer the APPROVED QA that *defines* it at a level
the asker can climb down to. Concepts with no such QA are returned as
gaps so the UI can show them honestly instead of dropping them. No LLM
or embedding calls: concepts and levels are already on the rows.
"""

import logging

from sqlalchemy.orm import Session

from physics_ai_tutor.models.concept import Concept
from physics_ai_tutor.models.question import Question
from physics_ai_tutor.models.question_concept import QuestionConcept
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.question import (
    PrerequisitesResponse,
    QuestionResponse,
    QuestionStatus,
)
from physics_ai_tutor.services.question_service import prepare_for_response

logger = logging.getLogger(__name__)

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
    return _is_definition_question(
        question.question_ja, concept.name_ja
    ) or _is_definition_question(question.question_en, concept.name_en)


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


def get_prerequisites(
    db: Session,
    question_id: int,
    limit: int = 5,
    language: Language | str = Language.JA,
) -> PrerequisitesResponse | None:
    lang = Language(language)

    current = db.get(Question, question_id)
    if current is None:
        return None

    links = (
        db.query(Concept, Question)
        .join(QuestionConcept, QuestionConcept.concept_id == Concept.id)
        .join(Question, Question.id == QuestionConcept.question_id)
        .filter(
            Concept.id.in_(
                db.query(QuestionConcept.concept_id)
                .filter(QuestionConcept.question_id == question_id)
                .scalar_subquery()
            ),
            Question.id != question_id,
            Question.status == QuestionStatus.APPROVED,
        )
        .all()
    )

    best_by_concept: dict[int, tuple[Concept, Question]] = {}
    concepts_seen: dict[int, Concept] = {}
    for concept, candidate in links:
        concepts_seen[concept.id] = concept
        if not _defines(candidate, concept):
            continue
        if not _not_more_advanced(candidate, current):
            continue
        best = best_by_concept.get(concept.id)
        # Prefer the least advanced definer; ties go to the older row.
        if best is None or _rank(candidate) < _rank(best[1]):
            best_by_concept[concept.id] = (concept, candidate)

    # Concepts of the current QA that ended up with no usable definer.
    current_concepts = (
        db.query(Concept)
        .join(QuestionConcept, QuestionConcept.concept_id == Concept.id)
        .filter(QuestionConcept.question_id == question_id)
        .all()
    )
    gaps = [
        concept.display_name(lang.value)
        for concept in current_concepts
        if concept.id not in best_by_concept
    ]

    # One card per QA even when it defines several concepts; hardest
    # prerequisite first - that is the one the stuck reader meets next.
    axis = _stuck_axis(current)
    unique: dict[int, Question] = {}
    for _, candidate in best_by_concept.values():
        unique[candidate.id] = candidate
    ordered = sorted(
        unique.values(),
        key=lambda q: (getattr(q, axis) or 0, -q.id),
        reverse=True,
    )[:limit]

    prepare_for_response(db, ordered, lang)

    logger.info(
        "Prerequisites computed: question_id=%d definers=%d gaps=%d",
        question_id,
        len(ordered),
        len(gaps),
    )

    return PrerequisitesResponse(
        items=[QuestionResponse.model_validate(question) for question in ordered],
        gaps=gaps,
    )
