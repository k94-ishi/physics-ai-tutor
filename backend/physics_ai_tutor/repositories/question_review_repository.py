from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from physics_ai_tutor.models import Question, QuestionReview


async def create(
    db: AsyncSession,
    question_id: int,
    action: str,
    reviewer_id: int,
    language: str = "ja",
    reason: str | None = None,
    before_question: str | None = None,
    before_answer: str | None = None,
    after_question: str | None = None,
    after_answer: str | None = None,
    comment: str | None = None,
) -> QuestionReview:
    review = QuestionReview(
        question_id=question_id,
        action=action,
        reviewer_id=reviewer_id,
        language=language,
        reason=reason,
        before_question=before_question,
        before_answer=before_answer,
        after_question=after_question,
        after_answer=after_answer,
        comment=comment,
    )

    db.add(review)
    await db.flush()

    return review


async def list_for_question(db: AsyncSession, question_id: int) -> list[QuestionReview]:
    query = (
        select(QuestionReview)
        .where(QuestionReview.question_id == question_id)
        .order_by(QuestionReview.created_at.desc())
    )
    return list((await db.scalars(query)).all())


def list_with_questions_since(
    db: Session,
    since: datetime | None,
) -> list[tuple[QuestionReview, Question]]:
    """Reviews joined to their question, oldest first; `since` is inclusive."""
    query = db.query(QuestionReview, Question).join(
        Question, QuestionReview.question_id == Question.id
    )

    if since is not None:
        query = query.filter(QuestionReview.created_at >= since)

    rows = query.order_by(QuestionReview.created_at.asc(), QuestionReview.id.asc())

    return [(review, question) for review, question in rows.all()]
