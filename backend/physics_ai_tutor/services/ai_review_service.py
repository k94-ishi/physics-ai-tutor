import json
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.prompt_library import load_library
from physics_ai_tutor.models import AiReview, AiReviewRun, Question
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


# Reviewer output quotes physics with LaTeX, and models mix properly
# doubled backslashes (\\text) with single ones (\eta) in one string.
# Rather than guess with a regex, let the decoder point at each invalid
# escape and double that backslash, bounded so garbage cannot loop.
MAX_ESCAPE_REPAIRS = 500


def _loads_with_escape_repair(text: str) -> dict | None:
    for _ in range(MAX_ESCAPE_REPAIRS):
        try:
            # strict=False accepts literal line breaks inside strings, which
            # multi-line suggested answers contain.
            data = json.loads(text, strict=False)
        except json.JSONDecodeError as exc:
            if exc.msg.startswith("Invalid \\escape") and exc.pos < len(text):
                text = text[: exc.pos] + "\\" + text[exc.pos :]
                continue
            return None
        return data if isinstance(data, dict) else None

    return None


def _parse_output(content: str) -> dict | None:
    """The JSON object from the model, or None when unparseable."""
    text = _strip_code_fences(content)
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end <= start:
        return None

    return _loads_with_escape_repair(text[start : end + 1])


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


def build_review_prompts(
    question_text: str,
    answer_text: str,
    language: Language,
    concepts: list[str] | None = None,
    context: str = "",
) -> tuple[str, str]:
    """The reviewer prompts for one Q&A; pure strings, no database needed."""
    user_prompt = _LIBRARY.get("ai_review", "user_template", language).format(
        question=question_text,
        answer=answer_text,
        concepts=", ".join(concepts) if concepts else "-",
        context=context,
    )

    return _LIBRARY.get("ai_review", "system", language), user_prompt


class GradedAnswer:
    """Parsed reviewer output plus the call's usage; verdict None = unparsed."""

    def __init__(self, result, data: dict | None) -> None:
        self.model = result.model
        self.prompt_tokens = result.prompt_tokens
        self.completion_tokens = result.completion_tokens
        self.raw = result.content

        if data is None:
            self.verdict = None
            self.confidence = None
            self.reasons: list[QuestionReviewReason] = []
            self.rationale: str | None = result.content[:5000]
            self.suggested_answer: str | None = None
            self.rubric: dict[str, int] | None = None
            self.parsed = False
        else:
            self.verdict = _coerce_verdict(data.get("verdict"))
            self.confidence = _coerce_confidence(data.get("confidence"))
            self.reasons = _coerce_reasons(data.get("reasons"))
            self.rationale = _optional_text(data.get("rationale"))
            self.suggested_answer = _optional_text(data.get("suggested_answer"))
            self.rubric = _coerce_rubric(data.get("rubric"))
            self.parsed = True


def grade_answer(
    question_text: str,
    answer_text: str,
    language: Language,
    concepts: list[str] | None = None,
    context: str = "",
    temperature: float | None = None,
) -> GradedAnswer:
    """Grade one Q&A with the rubric; database-free (used by the eval too)."""
    system_prompt, user_prompt = build_review_prompts(
        question_text, answer_text, language, concepts, context
    )
    result = deepseek_service.generate_answer(
        system_prompt,
        user_prompt,
        temperature=temperature,
        max_tokens=settings.ai_review_max_tokens,
    )

    return GradedAnswer(result, _parse_output(result.content))


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
        text = question.text(language) or question.original_text()
        concepts = question_concept_repository.get_concepts_for_questions(
            db, [question.id], language=language.value
        ).get(question.id, [])
        graded = grade_answer(
            text[0],
            text[1],
            language,
            concepts=concepts,
            context=_build_context(db, question, language),
        )
    except Exception:
        logger.warning(
            "AI review failed before storing: question_id=%d",
            question.id,
            exc_info=True,
        )
        db.rollback()
        return None

    review = AiReviewCreate(
        question_id=question.id,
        language=language,
        verdict=graded.verdict,
        confidence=graded.confidence,
        reasons=graded.reasons,
        rationale=graded.rationale,
        suggested_answer=graded.suggested_answer,
        rubric=graded.rubric,
        model=graded.model,
        prompt_version=REVIEW_PROMPT_VERSION,
        prompt_tokens=graded.prompt_tokens,
        completion_tokens=graded.completion_tokens,
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


# --- runs ----------------------------------------------------------------------

RUN_TIMEOUT_MINUTES = 30
CAP_WINDOW_HOURS = 24


class RunInProgressError(Exception):
    """Another AI review run is already running."""


class DailyCapExhaustedError(Exception):
    """The rolling 24h budget of reviewer calls is spent."""


def remaining_daily_budget(db: Session) -> int:
    used = ai_review_repository.count_created_since(db, CAP_WINDOW_HOURS)

    return max(settings.ai_review_daily_cap - used, 0)


def eligible_question_ids(
    db: Session,
    scope: str,
    question_ids: list[int] | None = None,
    limit: int | None = None,
) -> list[int]:
    bound = limit if limit is not None else settings.ai_review_daily_cap

    if scope == "pending":
        return ai_review_repository.list_pending_question_ids(db, bound)
    if scope == "stale":
        return ai_review_repository.list_stale_question_ids(
            db, REVIEW_PROMPT_VERSION, bound
        )
    if scope == "selected":
        return ai_review_repository.filter_reviewable_ids(db, question_ids or [])[
            :bound
        ]

    raise ValueError(f"Unknown scope: {scope}")


def _fail_timed_out_runs(db: Session) -> None:
    cutoff = datetime.now(UTC) - timedelta(minutes=RUN_TIMEOUT_MINUTES)

    db.query(AiReviewRun).filter(
        AiReviewRun.status == "running", AiReviewRun.started_at < cutoff
    ).update(
        {
            "status": "failed",
            "error": f"timed out after {RUN_TIMEOUT_MINUTES} minutes",
            "finished_at": func.now(),
        }
    )


def start_run(
    db: Session,
    scope: str,
    trigger: str,
    question_ids: list[int] | None = None,
    limit: int | None = None,
    started_by: int | None = None,
) -> AiReviewRun:
    """Create the run row with its fixed question list; raises on conflicts.

    The partial unique index on status='running' is the real guard; the
    pre-check only produces a friendlier error for the common case.
    """
    _fail_timed_out_runs(db)

    running = db.query(AiReviewRun).filter(AiReviewRun.status == "running").first()
    if running is not None:
        db.rollback()
        raise RunInProgressError(str(running.id))

    budget = remaining_daily_budget(db)
    if budget <= 0:
        db.rollback()
        raise DailyCapExhaustedError(str(settings.ai_review_daily_cap))

    ids = eligible_question_ids(db, scope, question_ids, limit)[:budget]

    run = AiReviewRun(
        trigger=trigger,
        scope=scope,
        started_by_user_id=started_by,
        question_ids=ids,
        requested_count=len(ids),
        status="running",
    )
    db.add(run)

    try:
        db.commit()
    except IntegrityError as exc:
        # Lost the race against a concurrent start.
        db.rollback()
        raise RunInProgressError("concurrent start") from exc

    return run


def execute_run(db: Session, run_id: int) -> AiReviewRun | None:
    """Process the run's fixed question list, committing progress per item."""
    run = db.get(AiReviewRun, run_id)
    if run is None or run.status != "running":
        return run

    try:
        for question_id in run.question_ids:
            question = db.get(Question, question_id)
            row = review_question(db, question) if question is not None else None

            if row is None:
                run.failed_count += 1
            else:
                run.reviewed_count += 1
                run.prompt_tokens += row.prompt_tokens or 0
                run.completion_tokens += row.completion_tokens or 0

            # Commit after every question so progress polling sees it.
            db.commit()

        run.status = "done"
        run.finished_at = datetime.now(UTC)
        db.commit()
    except Exception:
        logger.exception("AI review run failed: run_id=%d", run_id)
        db.rollback()
        run.status = "failed"
        run.error = "unexpected error; see server logs"
        run.finished_at = datetime.now(UTC)
        db.commit()

    return run
