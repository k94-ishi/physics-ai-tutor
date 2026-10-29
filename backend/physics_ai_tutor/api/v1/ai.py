import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from physics_ai_tutor.api.dependencies import (
    AiAskRateLimit,
    enforce_ai_ask_rate_limit,
    get_current_user_optional,
)
from physics_ai_tutor.core import prompts
from physics_ai_tutor.core.config import settings
from physics_ai_tutor.database.database import SessionLocal
from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.models import Question
from physics_ai_tutor.schemas.ai import AskAiRequest, AskAiResponse
from physics_ai_tutor.schemas.question import (
    GenerationMeta,
    QuestionSource,
    QuestionStatus,
)
from physics_ai_tutor.schemas.token import JWTPayload
from physics_ai_tutor.services import (
    ai_review_service,
    ask_history_service,
    deepseek_service,
    question_service,
    rag_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


def post_generation_tasks(question_id: int) -> None:
    """After the response is sent: translate, then (if enabled) AI-review.

    Each step is best-effort and isolated; a failure in one must not stop
    the other, and neither can affect the already-sent answer.
    """
    db = SessionLocal()
    try:
        try:
            question_service.translate_missing_languages(db, question_id)
        except Exception:
            logger.warning(
                "Background translation failed: question_id=%d",
                question_id,
                exc_info=True,
            )
            db.rollback()

        if settings.ai_review_enabled:
            question = db.get(Question, question_id)
            if question is not None:
                ai_review_service.review_question(db, question)
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
        result, retrieved_ids = rag_service.generate_rag_answer(
            db, request.question, request.retrieved_question_ids, request.language
        )
        source = QuestionSource.RAG_RESULT
        generation_mode = "RAG"
    else:
        result = deepseek_service.generate_answer(
            prompts.SYSTEM_PROMPTS[request.language], request.question
        )
        retrieved_ids = []
        source = QuestionSource.AI_GENERATED
        generation_mode = "DIRECT"

    answer = result.content

    # A declined off-topic question is returned but never saved: it must not
    # enter the knowledge base nor be served from the cache to someone else.
    # The asker's quota stays spent - the LLM call did happen.
    stripped = answer.lstrip()
    if stripped.startswith(prompts.OFF_TOPIC_SENTINEL):
        message = stripped[len(prompts.OFF_TOPIC_SENTINEL) :].strip()
        logger.info(
            "Ask AI declined off-topic question: bucket=%s mode=%s",
            rate_limit.bucket_key,
            generation_mode,
        )
        return AskAiResponse(
            answer=message or prompts.OFF_TOPIC_FALLBACK[request.language],
            language=request.language,
        )

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
        generation=GenerationMeta(
            model=result.model,
            prompt_version=prompts.ANSWER_PROMPT_VERSION,
            mode=generation_mode,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
        ),
    )

    if saved is not None:
        if user is not None:
            ask_history_service.record_ask(
                db, saved.id, int(user.sub), request.language, cache_hit=False
            )
        background_tasks.add_task(post_generation_tasks, saved.id)

    return AskAiResponse(
        answer=answer,
        language=request.language,
        question_id=saved.id if saved else None,
        status=QuestionStatus.UNREVIEWED if saved else None,
    )
