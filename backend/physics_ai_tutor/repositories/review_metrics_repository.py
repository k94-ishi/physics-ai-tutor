from dataclasses import dataclass
from datetime import datetime

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


def list_pairs(db: Session, since: datetime | None) -> list[ReviewPair]:
    """Pair each human review with the latest AI review created before it.

    Human reviews with no earlier AI verdict (the backlog case) are left
    out: they say nothing about the reviewer's accuracy.
    """
    query = (
        db.query(QuestionReview, Question)
        .join(Question, QuestionReview.question_id == Question.id)
        .filter(
            QuestionReview.reviewer_kind == "human",
            QuestionReview.action.in_(HUMAN_ACTIONS),
        )
    )
    if since is not None:
        query = query.filter(QuestionReview.created_at >= since)

    reviews = query.order_by(QuestionReview.created_at.asc()).all()
    if not reviews:
        return []

    ai_rows = (
        db.query(AiReview)
        .filter(AiReview.question_id.in_({r.question_id for r, _ in reviews}))
        .order_by(AiReview.created_at.asc(), AiReview.id.asc())
        .all()
    )
    ai_by_question: dict[int, list[AiReview]] = {}
    for row in ai_rows:
        ai_by_question.setdefault(row.question_id, []).append(row)

    pairs = []
    for review, question in reviews:
        earlier = [
            row
            for row in ai_by_question.get(question.id, [])
            if row.created_at < review.created_at
        ]
        if not earlier:
            continue

        ai = earlier[-1]
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
