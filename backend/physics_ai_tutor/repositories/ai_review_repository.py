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
