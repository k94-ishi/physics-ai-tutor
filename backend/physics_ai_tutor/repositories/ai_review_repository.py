from datetime import timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from physics_ai_tutor.models import AiReview, Question
from physics_ai_tutor.schemas.ai_review import AiReviewCreate


def _new_review(review: AiReviewCreate) -> AiReview:
    return AiReview(
        question_id=review.question_id,
        language=review.language.value,
        verdict=review.verdict.value if review.verdict else None,
        confidence=review.confidence,
        reasons=[reason.value for reason in review.reasons],
        rationale=review.rationale,
        suggested_answer=review.suggested_answer,
        rubric=review.rubric,
        model=review.model,
        prompt_version=review.prompt_version,
        prompt_tokens=review.prompt_tokens,
        completion_tokens=review.completion_tokens,
    )


def create(db: Session, review: AiReviewCreate) -> AiReview:
    row = _new_review(review)

    db.add(row)
    db.flush()

    return row


async def async_create(db: AsyncSession, review: AiReviewCreate) -> AiReview:
    row = _new_review(review)

    db.add(row)
    await db.flush()

    return row


def get_latest_for_question(db: Session, question_id: int) -> AiReview | None:
    return (
        db.query(AiReview)
        .filter(AiReview.question_id == question_id)
        .order_by(AiReview.created_at.desc(), AiReview.id.desc())
        .first()
    )


def list_for_question(db: Session, question_id: int) -> list[AiReview]:
    return (
        db.query(AiReview)
        .filter(AiReview.question_id == question_id)
        .order_by(AiReview.created_at.desc(), AiReview.id.desc())
        .all()
    )


def _latest_for_questions_select(ids: list[int]):
    return (
        select(AiReview)
        .where(AiReview.question_id.in_(ids))
        .order_by(AiReview.question_id, AiReview.id.desc())
    )


def _newest_per_question(rows) -> dict[int, AiReview]:
    latest: dict[int, AiReview] = {}
    for row in rows:
        latest.setdefault(row.question_id, row)

    return latest


async def async_latest_for_questions(
    db: AsyncSession, ids: list[int]
) -> dict[int, AiReview]:
    """As `latest_for_questions` ([83]); the sync one serves the review flow."""
    if not ids:
        return {}

    rows = (await db.scalars(_latest_for_questions_select(ids))).all()

    return _newest_per_question(rows)


# A verdict the parser could not read leaves a NULL-verdict row. Such a
# question still has no usable verdict, so it stays pending - but only for
# this many attempts, or a reliably unparseable answer would be re-reviewed
# on every run forever.
MAX_PARSE_ATTEMPTS = 3


def _pending_question_select() -> Select[tuple[int]]:
    """UNREVIEWED AI questions with no usable verdict yet, oldest first.

    One statement for the list and the count, so they cannot disagree.
    """
    graded = select(AiReview.question_id).where(AiReview.verdict.isnot(None))
    exhausted = (
        select(AiReview.question_id)
        .group_by(AiReview.question_id)
        .having(func.count(AiReview.id) >= MAX_PARSE_ATTEMPTS)
    )

    return (
        select(Question.id)
        .where(
            Question.status == "UNREVIEWED",
            Question.source.in_(["AI_GENERATED", "RAG_RESULT"]),
            ~Question.id.in_(graded),
            ~Question.id.in_(exhausted),
        )
        .order_by(Question.id.asc())
    )


def _count_of(query: Select[tuple[int]]) -> Select[tuple[int]]:
    """`SELECT count(*)` over a statement, as `Query.count()` did."""
    return select(func.count()).select_from(query.order_by(None).subquery())


async def async_list_pending_question_ids(db: AsyncSession, limit: int) -> list[int]:
    """Pending question ids, oldest first, at most `limit`."""
    query = _pending_question_select().limit(limit)

    return list((await db.scalars(query)).all())


async def async_count_pending_questions(db: AsyncSession) -> int:
    """The true total, unbounded by any run's limit or the daily cap."""
    return (await db.scalar(_count_of(_pending_question_select()))) or 0


def _created_since_count(hours: int) -> Select[tuple[int]]:
    cutoff = func.now() - timedelta(hours=hours)

    return select(func.count(AiReview.id)).where(AiReview.created_at > cutoff)


async def async_count_created_since(db: AsyncSession, hours: int) -> int:
    """AI reviews created in the last `hours`, for the daily cap."""
    return (await db.scalar(_created_since_count(hours))) or 0


def _stale_question_select(current_version: str) -> Select[tuple[int]]:
    """UNREVIEWED AI questions whose latest verdict used an older prompt."""
    latest = (
        select(
            AiReview.question_id,
            func.max(AiReview.id).label("latest_id"),
        )
        .group_by(AiReview.question_id)
        .subquery()
    )

    return (
        select(Question.id)
        .join(latest, latest.c.question_id == Question.id)
        .join(AiReview, AiReview.id == latest.c.latest_id)
        .where(
            Question.status == "UNREVIEWED",
            Question.source.in_(["AI_GENERATED", "RAG_RESULT"]),
            AiReview.prompt_version != current_version,
        )
        .order_by(Question.id.asc())
    )


async def async_list_stale_question_ids(
    db: AsyncSession, current_version: str, limit: int
) -> list[int]:
    """Stale question ids, oldest first, at most `limit`."""
    query = _stale_question_select(current_version).limit(limit)

    return list((await db.scalars(query)).all())


async def async_count_stale_questions(db: AsyncSession, current_version: str) -> int:
    """The true total, unbounded by any run's limit or the daily cap."""
    query = _count_of(_stale_question_select(current_version))

    return (await db.scalar(query)) or 0


def _reviewable_select(ids: list[int]) -> Select[tuple[int]]:
    """The given ids that are still UNREVIEWED AI questions."""
    return select(Question.id).where(
        Question.id.in_(ids),
        Question.status == "UNREVIEWED",
        Question.source.in_(["AI_GENERATED", "RAG_RESULT"]),
    )


def _in_given_order(ids: list[int], eligible: set[int]) -> list[int]:
    return [question_id for question_id in ids if question_id in eligible]


async def async_filter_reviewable_ids(db: AsyncSession, ids: list[int]) -> list[int]:
    """Keep only UNREVIEWED AI questions, preserving the given order."""
    if not ids:
        return []

    eligible = set((await db.scalars(_reviewable_select(ids))).all())

    return _in_given_order(ids, eligible)
