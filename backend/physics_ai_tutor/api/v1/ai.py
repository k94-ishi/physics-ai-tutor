import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from physics_ai_tutor.api.dependencies import (
    AiAskRateLimit,
    enforce_ai_ask_rate_limit,
    get_current_user_optional,
)
from physics_ai_tutor.core import prompts
from physics_ai_tutor.database.database import SessionLocal
from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.schemas.ai import AskAiRequest, AskAiResponse
from physics_ai_tutor.schemas.question import QuestionSource, QuestionStatus
from physics_ai_tutor.schemas.token import JWTPayload
from physics_ai_tutor.services import (
    ask_history_service,
    deepseek_service,
    question_service,
    rag_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


def translate_in_background(question_id: int) -> None:
    """Fill the other language after the response has been sent."""
    db = SessionLocal()
    try:
        question_service.translate_missing_languages(db, question_id)
    except Exception:
        logger.warning(
            "Background translation failed: question_id=%d", question_id, exc_info=True
        )
    finally:
        db.close()


@router.post("/ask", response_model=AskAiResponse)
def ask_ai(
    request: AskAiRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    rate_limit: AiAskRateLimit = Depends(enforce_ai_ask_rate_limit),
    user: JWTPayload | None = Depends(get_current_user_optional),
):
    # Cache tier 0: an identical question was already answered (any status
    # except rejected), so reuse it instead of paying for generation again.
    cached = question_service.find_cached_answer(db, request.question, request.language)
    if cached is not None:
        if user is not None:
            ask_history_service.record_ask(
                db, cached.id, int(user.sub), request.language, cache_hit=True
            )
        text = cached.text(request.language)
        assert text is not None
        logger.info(
            "Ask AI served from cache: question_id=%d status=%s",
            cached.id,
            cached.status,
        )
        return AskAiResponse(
            answer=text[1],
            language=request.language,
            cached=True,
            question_id=cached.id,
            status=QuestionStatus(cached.status),
        )

    # Only a cache miss costs quota; it is about to trigger a generation.
    rate_limit.record(db)

    if request.mode == "RAG":
        answer, retrieved_ids = rag_service.generate_rag_answer(
            db, request.question, request.retrieved_question_ids, request.language
        )
        source = QuestionSource.RAG_RESULT
    else:
        answer = deepseek_service.chat_completion(
            prompts.SYSTEM_PROMPTS[request.language], request.question
        )
        retrieved_ids = []
        source = QuestionSource.AI_GENERATED

    logger.info(
        "Ask AI request answered: question_length=%d mode=%s language=%s",
        len(request.question),
        request.mode,
        request.language,
    )

    saved = question_service.save_ai_question(
        db,
        request.question,
        answer,
        language=request.language,
        source=source,
        retrieved_question_ids=retrieved_ids,
    )

    if saved is not None:
        if user is not None:
            ask_history_service.record_ask(
                db, saved.id, int(user.sub), request.language, cache_hit=False
            )
        background_tasks.add_task(translate_in_background, saved.id)

    return AskAiResponse(
        answer=answer,
        language=request.language,
        question_id=saved.id if saved else None,
        status=QuestionStatus.UNREVIEWED if saved else None,
    )
