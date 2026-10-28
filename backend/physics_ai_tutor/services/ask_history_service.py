import logging

from sqlalchemy.orm import Session

from physics_ai_tutor.repositories import question_ask_repository
from physics_ai_tutor.schemas.ask_history import MyQuestionEntry, MyQuestionsResponse
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.question import QuestionStatus

logger = logging.getLogger(__name__)


def record_ask(
    db: Session,
    question_id: int,
    user_id: int,
    language: Language | str,
) -> None:
    """Best-effort: a failed history row must not fail the answer."""
    try:
        question_ask_repository.create(
            db, question_id, user_id, Language(language).value
        )
        db.commit()

        logger.info("Ask recorded: question_id=%d user_id=%d", question_id, user_id)
    except Exception:
        logger.warning(
            "Recording ask failed: question_id=%d user_id=%d",
            question_id,
            user_id,
            exc_info=True,
        )
        db.rollback()


def fetch_my_questions(
    db: Session,
    user_id: int,
    page: int,
    size: int,
    language: Language | str,
) -> MyQuestionsResponse:
    lang = Language(language)
    rows = question_ask_repository.list_for_user(
        db, user_id, offset=(page - 1) * size, limit=size
    )
    total = question_ask_repository.count_for_user(db, user_id)

    items = []
    for ask, question in rows:
        text = question.text(lang) or question.original_text()
        served = lang if question.has(lang) else Language(question.original_language)
        status = QuestionStatus(question.status)
        rejected = status == QuestionStatus.REJECTED

        items.append(
            MyQuestionEntry(
                question_id=question.id,
                question=text[0],
                # The rejected text was withdrawn by a teacher; don't serve it.
                answer=None if rejected else text[1],
                language=served,
                provenance=question.provenance_of(served),
                status=status,
                asked_at=ask.created_at,
            )
        )

    return MyQuestionsResponse(items=items, total=total, page=page, size=size)
