from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from physics_ai_tutor.models import AiReview, Question, QuestionReview

HUMAN_ACTIONS = ("APPROVE", "EDIT_APPROVE", "REJECT")


@dataclass(frozen=True)
class ReviewPair:
    """One human review matched with the AI verdict that preceded it."""

    question_id: int
    human_action: str
    human_reason: str | None
    ai_verdict: str | None
    ai_confidence: float | None
    ai_reasons: tuple[str, ...]
    answer_prompt_version: str | None
    reviewer_prompt_version: str
    reviewed_at: datetime


def _ai_reviews_select(question_ids: set[int]) -> Select[tuple[AiReview]]:
    """One statement for both twins, so their order cannot drift."""
    return (
        select(AiReview)
        .where(AiReview.question_id.in_(question_ids))
        .order_by(AiReview.created_at.asc(), AiReview.id.asc())
    )


def _group_by_question(rows: Iterable[AiReview]) -> dict[int, list[AiReview]]:
    grouped: dict[int, list[AiReview]] = {}
    for row in rows:
        grouped.setdefault(row.question_id, []).append(row)

    return grouped


def ai_reviews_by_question(
    db: Session, question_ids: set[int]
) -> dict[int, list[AiReview]]:
    """All AI reviews for the given questions, oldest first per question.

    Sync twin for review_export_service until [96] converts it.
    """
    if not question_ids:
        return {}

    return _group_by_question(db.scalars(_ai_reviews_select(question_ids)).all())


async def async_ai_reviews_by_question(
    db: AsyncSession, question_ids: set[int]
) -> dict[int, list[AiReview]]:
    """As `ai_reviews_by_question`, on an `AsyncSession` ([87])."""
    if not question_ids:
        return {}

    rows = (await db.scalars(_ai_reviews_select(question_ids))).all()

    return _group_by_question(rows)


def ai_review_before(
    candidates: list[AiReview], reviewed_at: datetime
) -> AiReview | None:
    """The latest AI review that existed when the human reviewed."""
    earlier = [row for row in candidates if row.created_at < reviewed_at]

    return earlier[-1] if earlier else None


async def list_pairs(db: AsyncSession, since: datetime | None) -> list[ReviewPair]:
    """Pair each human review with the latest AI review created before it.

    Human reviews with no earlier AI verdict (the backlog case) are left
    out: they say nothing about the reviewer's accuracy.
    """
    query = (
        select(QuestionReview, Question)
        .join(Question, QuestionReview.question_id == Question.id)
        .where(
            QuestionReview.reviewer_kind == "human",
            QuestionReview.action.in_(HUMAN_ACTIONS),
        )
    )
    if since is not None:
        query = query.where(QuestionReview.created_at >= since)

    result = await db.execute(query.order_by(QuestionReview.created_at.asc()))
    reviews = result.tuples().all()
    if not reviews:
        return []

    ai_by_question = await async_ai_reviews_by_question(
        db, {review.question_id for review, _ in reviews}
    )

    pairs = []
    for review, question in reviews:
        ai = ai_review_before(ai_by_question.get(question.id, []), review.created_at)
        if ai is None:
            continue

        pairs.append(
            ReviewPair(
                question_id=question.id,
                human_action=review.action,
                human_reason=review.reason,
                ai_verdict=ai.verdict,
                ai_confidence=ai.confidence,
                ai_reasons=tuple(ai.reasons or []),
                answer_prompt_version=question.prompt_version,
                reviewer_prompt_version=ai.prompt_version,
                reviewed_at=review.created_at,
            )
        )

    return pairs
