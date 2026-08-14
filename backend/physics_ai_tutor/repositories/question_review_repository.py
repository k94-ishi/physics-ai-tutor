from sqlalchemy.orm import Session

from physics_ai_tutor.models import QuestionReview


def create(
    db: Session,
    question_id: int,
    action: str,
    reviewer_id: int,
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
        before_question=before_question,
        before_answer=before_answer,
        after_question=after_question,
        after_answer=after_answer,
        comment=comment,
    )

    db.add(review)
    db.flush()

    return review


def list_for_question(db: Session, question_id: int) -> list[QuestionReview]:
    return (
        db.query(QuestionReview)
        .filter(QuestionReview.question_id == question_id)
        .order_by(QuestionReview.created_at.desc())
        .all()
    )
