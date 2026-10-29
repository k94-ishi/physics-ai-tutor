import json
import logging

from sqlalchemy.orm import Session

from physics_ai_tutor.core.prompt_library import load_library
from physics_ai_tutor.models import AiReview, Question
from physics_ai_tutor.repositories import (
    ai_review_repository,
    question_concept_repository,
)
from physics_ai_tutor.schemas.ai_review import AiReviewCreate, AiReviewVerdict
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.question import QuestionSource, QuestionStatus
from physics_ai_tutor.schemas.question_review import QuestionReviewReason
from physics_ai_tutor.services import deepseek_service, rag_service

logger = logging.getLogger(__name__)

_LIBRARY = load_library()

REVIEW_PROMPT_VERSION = _LIBRARY.version("ai_review")

RUBRIC_CRITERIA = [
    "physics",
    "math",
    "completeness",
    "level",
    "clarity",
    "formatting",
    "scope",
]

AI_SOURCES = (QuestionSource.AI_GENERATED, QuestionSource.RAG_RESULT)


def _strip_code_fences(content: str) -> str:
    text = content.strip()

    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]

    return text.strip()


def _parse_output(content: str) -> dict | None:
    """The JSON object from the model, or None when unparseable."""
    text = _strip_code_fences(content)
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end <= start:
        return None

    try:
        data = json.loads(text[start : end + 1])
    except ValueError:
        return None

    return data if isinstance(data, dict) else None


def _coerce_verdict(value: object) -> AiReviewVerdict | None:
    try:
        return AiReviewVerdict(str(value))
    except ValueError:
        return None


def _coerce_confidence(value: object) -> float | None:
    try:
        confidence = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None

    return min(max(confidence, 0.0), 1.0)


def _coerce_reasons(value: object) -> list[QuestionReviewReason]:
    if not isinstance(value, list):
        return []

    reasons = []
    for item in value:
        try:
            reasons.append(QuestionReviewReason(str(item)))
        except ValueError:
            logger.info("AI review returned unknown reason code: %r", item)

    return reasons


def _coerce_rubric(value: object) -> dict[str, int] | None:
    if not isinstance(value, dict):
        return None

    rubric = {}
    for criterion in RUBRIC_CRITERIA:
        score = value.get(criterion)
        if isinstance(score, int) and 0 <= score <= 2:
            rubric[criterion] = score

    return rubric or None


def _optional_text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value

    return None


def _build_context(db: Session, question: Question, language: Language) -> str:
    """Approved reference QA blocks for RAG-grounded answers, if any."""
    ids = list(question.retrieved_question_ids or [])
    if not ids:
        return ""

    references = rag_service.load_context_by_ids(db, ids, language)
    if not references:
        return ""

    header = _LIBRARY.get("ai_review", "context_header", language)
    blocks = "\n\n".join(f"Q: {item.question}\nA: {item.answer}" for item in references)

    return f"\n{header}{blocks}\n"


def _build_prompts(
    db: Session, question: Question, language: Language
) -> tuple[str, str]:
    text = question.text(language) or question.original_text()
    concepts = question_concept_repository.get_concepts_for_questions(
        db, [question.id], language=language.value
    ).get(question.id, [])

    user_prompt = _LIBRARY.get("ai_review", "user_template", language).format(
        question=text[0],
        answer=text[1],
        concepts=", ".join(concepts) if concepts else "-",
        context=_build_context(db, question, language),
    )

    return _LIBRARY.get("ai_review", "system", language), user_prompt


def review_question(db: Session, question: Question) -> AiReview | None:
    """Grade one UNREVIEWED AI answer and store the verdict. Advisory only.

    Never raises and never touches the question's status; a reviewer
    failure must not affect the student-facing flow.
    """
    if question.source not in AI_SOURCES:
        logger.info("AI review skipped: question_id=%d reason=not_ai", question.id)
        return None

    if question.status != QuestionStatus.UNREVIEWED:
        logger.info(
            "AI review skipped: question_id=%d reason=already_reviewed", question.id
        )
        return None

    language = Language(question.original_language)

    try:
        system_prompt, user_prompt = _build_prompts(db, question, language)
        result = deepseek_service.generate_answer(system_prompt, user_prompt)
    except Exception:
        logger.warning(
            "AI review failed before storing: question_id=%d",
            question.id,
            exc_info=True,
        )
        db.rollback()
        return None

    data = _parse_output(result.content)

    if data is None:
        # Keep the failure visible instead of silently dropping it.
        review = AiReviewCreate(
            question_id=question.id,
            language=language,
            verdict=None,
            rationale=result.content[:5000],
            model=result.model,
            prompt_version=REVIEW_PROMPT_VERSION,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
        )
    else:
        review = AiReviewCreate(
            question_id=question.id,
            language=language,
            verdict=_coerce_verdict(data.get("verdict")),
            confidence=_coerce_confidence(data.get("confidence")),
            reasons=_coerce_reasons(data.get("reasons")),
            rationale=_optional_text(data.get("rationale")),
            suggested_answer=_optional_text(data.get("suggested_answer")),
            rubric=_coerce_rubric(data.get("rubric")),
            model=result.model,
            prompt_version=REVIEW_PROMPT_VERSION,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
        )

    try:
        row = ai_review_repository.create(db, review)
        db.commit()
    except Exception:
        logger.warning(
            "Storing AI review failed: question_id=%d", question.id, exc_info=True
        )
        db.rollback()
        return None

    logger.info(
        "AI review stored: question_id=%d verdict=%s confidence=%s",
        question.id,
        row.verdict,
        row.confidence,
    )

    return row
