import logging

from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.database.transaction import async_transaction
from physics_ai_tutor.repositories import question_ask_repository
from physics_ai_tutor.schemas.ask_history import MyQuestionEntry, MyQuestionsResponse
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.question import QuestionStatus

logger = logging.getLogger(__name__)


async def record_ask(
    db: AsyncSession,
    question_id: int,
    user_id: int,
    language: Language | str,
    cache_hit: bool,
) -> None:
    """As `record_ask`; still best effort ([70])."""
    try:
        async with async_transaction(db, "record_ask"):
            await question_ask_repository.create(
                db, question_id, user_id, Language(language).value, cache_hit=cache_hit
            )
    except Exception:
        logger.warning(
            "Recording ask failed: question_id=%d user_id=%d",
            question_id,
            user_id,
            exc_info=True,
        )
        return

    logger.info("Ask recorded: question_id=%d user_id=%d", question_id, user_id)


async def fetch_my_questions(
    db: AsyncSession,
    user_id: int,
    page: int,
    size: int,
    language: Language | str,
) -> MyQuestionsResponse:
    lang = Language(language)
    rows = await question_ask_repository.list_for_user(
        db, user_id, offset=(page - 1) * size, limit=size
    )
    total = await question_ask_repository.count_for_user(db, user_id)

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
