"""Backfill AI reviews for unreviewed AI answers that have none yet.

Runs regardless of AI_REVIEW_ENABLED: invoking the command is the intent.
Each question costs one DeepSeek call.
"""

import argparse

from physics_ai_tutor.database.database import SessionLocal
from physics_ai_tutor.models import Question
from physics_ai_tutor.repositories import ai_review_repository
from physics_ai_tutor.services import ai_review_service


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, default=20, help="Maximum questions to review."
    )
    return parser.parse_args()


def main(limit: int = 20) -> int:
    db = SessionLocal()
    reviewed = 0

    try:
        for question_id in ai_review_repository.list_pending_question_ids(db, limit):
            question = db.get(Question, question_id)
            if question is None:
                continue
            if ai_review_service.review_question(db, question) is not None:
                reviewed += 1
    finally:
        db.close()

    print(f"Reviewed {reviewed} questions")
    return reviewed


if __name__ == "__main__":
    args = parse_args()
    main(args.limit)
