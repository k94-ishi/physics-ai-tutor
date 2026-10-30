from sqlalchemy.orm import Session

from physics_ai_tutor.models import AiReview
from physics_ai_tutor.schemas.ai_review import AiReviewCreate


def create(db: Session, review: AiReviewCreate) -> AiReview:
    row = AiReview(
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

    db.add(row)
    db.flush()

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


def latest_for_questions(db: Session, ids: list[int]) -> dict[int, AiReview]:
    """question_id -> newest AiReview, for the ids that have one."""
    if not ids:
        return {}

    rows = (
        db.query(AiReview)
        .filter(AiReview.question_id.in_(ids))
        .order_by(AiReview.question_id, AiReview.id.desc())
        .all()
    )

    latest: dict[int, AiReview] = {}
    for row in rows:
        latest.setdefault(row.question_id, row)

    return latest


def list_pending_question_ids(db: Session, limit: int) -> list[int]:
    """UNREVIEWED AI questions that have no AI review yet, oldest first."""
    from physics_ai_tutor.models import Question

    reviewed = db.query(AiReview.question_id)

    rows = (
        db.query(Question.id)
        .filter(
            Question.status == "UNREVIEWED",
            Question.source.in_(["AI_GENERATED", "RAG_RESULT"]),
            ~Question.id.in_(reviewed),
        )
        .order_by(Question.id.asc())
        .limit(limit)
        .all()
    )

    return [question_id for (question_id,) in rows]


def count_created_since(db: Session, hours: int) -> int:
    """AI reviews created in the last `hours`, for the daily cap."""
    from datetime import timedelta

    from sqlalchemy import func

    cutoff = func.now() - timedelta(hours=hours)

    return (
        db.query(func.count(AiReview.id)).filter(AiReview.created_at > cutoff).scalar()
    ) or 0


def list_stale_question_ids(db: Session, current_version: str, limit: int) -> list[int]:
    """UNREVIEWED AI questions whose latest verdict used an older prompt."""
    from sqlalchemy import func

    from physics_ai_tutor.models import Question

    latest = (
        db.query(
            AiReview.question_id,
            func.max(AiReview.id).label("latest_id"),
        )
        .group_by(AiReview.question_id)
        .subquery()
    )

    rows = (
        db.query(Question.id)
        .join(latest, latest.c.question_id == Question.id)
        .join(AiReview, AiReview.id == latest.c.latest_id)
        .filter(
            Question.status == "UNREVIEWED",
            Question.source.in_(["AI_GENERATED", "RAG_RESULT"]),
            AiReview.prompt_version != current_version,
        )
        .order_by(Question.id.asc())
        .limit(limit)
        .all()
    )

    return [question_id for (question_id,) in rows]


def filter_reviewable_ids(db: Session, ids: list[int]) -> list[int]:
    """Keep only UNREVIEWED AI questions, preserving the given order."""
    from physics_ai_tutor.models import Question

    if not ids:
        return []

    rows = (
        db.query(Question.id)
        .filter(
            Question.id.in_(ids),
            Question.status == "UNREVIEWED",
            Question.source.in_(["AI_GENERATED", "RAG_RESULT"]),
        )
        .all()
    )
    eligible = {question_id for (question_id,) in rows}

    return [question_id for question_id in ids if question_id in eligible]
