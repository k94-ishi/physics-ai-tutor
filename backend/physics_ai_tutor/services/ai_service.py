"""The ask-AI use case: cache, generate, save, record ([59]).

Moved out of the router so the router only parses, authorises and calls
this. Behaviour is unchanged; see docs/api.md (AI) for the flow.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from physics_ai_tutor.core import prompts, timing
from physics_ai_tutor.core.config import settings
from physics_ai_tutor.database.session import background_session
from physics_ai_tutor.models import Question
from physics_ai_tutor.schemas.ai import AskAiRequest, AskAiResponse
from physics_ai_tutor.schemas.question import (
    GenerationMeta,
    QuestionSource,
    QuestionStatus,
)
from physics_ai_tutor.services import (
    ai_review_service,
    ask_history_service,
    deepseek_service,
    question_read_service,
    question_translation_service,
    question_write_service,
    rag_service,
)

logger = logging.getLogger(__name__)


@dataclass
class AskOutcome:
    response: AskAiResponse
    # Set when a new row was saved and needs the post-generation tasks.
    saved_question_id: int | None = None


def _from_cache(
    db: Session, request: AskAiRequest, user_id: int | None
) -> AskAiResponse | None:
    """Cache tier 0: reuse an identical, non-rejected question's answer."""
    with timing.stage("ask_cache_lookup") as stage:
        cached = question_read_service.find_cached_answer(
            db, request.question, request.language
        )
        stage.note(hit=cached is not None)

    if cached is None:
        return None
    if user_id is not None:
        ask_history_service.record_ask(
            db, cached.id, user_id, request.language, cache_hit=True
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


def _generate(db: Session, request: AskAiRequest):
    """Call the LLM in the requested mode; returns (result, ids, source, mode)."""
    if request.mode == "RAG":
        result, retrieved_ids = rag_service.generate_rag_answer(
            db, request.question, request.retrieved_question_ids, request.language
        )
        return result, retrieved_ids, QuestionSource.RAG_RESULT, "RAG"
    result = deepseek_service.generate_answer(
        prompts.SYSTEM_PROMPTS[request.language], request.question
    )
    return result, [], QuestionSource.AI_GENERATED, "DIRECT"


def _declined_message(answer: str, request: AskAiRequest) -> str | None:
    """The polite refusal when the model marked the question off-topic."""
    stripped = answer.lstrip()
    if not stripped.startswith(prompts.OFF_TOPIC_SENTINEL):
        return None
    message = stripped[len(prompts.OFF_TOPIC_SENTINEL) :].strip()
    return message or prompts.OFF_TOPIC_FALLBACK[request.language]


def ask(
    db: Session,
    request: AskAiRequest,
    user_id: int | None,
    record_generation: Callable[[], None],
    rate_limit_bucket: str,
) -> AskOutcome:
    """Answer one question; `record_generation` spends quota on a cache miss."""
    cached = _from_cache(db, request, user_id)
    if cached is not None:
        return AskOutcome(cached)

    # Only a cache miss costs quota; it is about to trigger a generation.
    record_generation()
    result, retrieved_ids, source, mode = _generate(db, request)

    # A declined off-topic question is returned but never saved: it must not
    # enter the knowledge base nor be served from the cache to someone else.
    # The asker's quota stays spent - the LLM call did happen.
    declined = _declined_message(result.content, request)
    if declined is not None:
        logger.info(
            "Ask AI declined off-topic question: bucket=%s mode=%s",
            rate_limit_bucket,
            mode,
        )
        return AskOutcome(AskAiResponse(answer=declined, language=request.language))

    logger.info(
        "Ask AI request answered: question_length=%d mode=%s language=%s",
        len(request.question),
        request.mode,
        request.language,
    )
    saved_id = _save_answer(db, request, user_id, result, retrieved_ids, source, mode)
    return AskOutcome(
        AskAiResponse(
            answer=result.content,
            language=request.language,
            question_id=saved_id,
            status=QuestionStatus.UNREVIEWED if saved_id is not None else None,
        ),
        saved_question_id=saved_id,
    )


def _save_answer(
    db: Session,
    request: AskAiRequest,
    user_id: int | None,
    result,
    retrieved_ids: list[int],
    source: QuestionSource,
    mode: str,
) -> int | None:
    """Store the answer as UNREVIEWED and record the ask; None if not saved."""
    with timing.stage("save_answer"):
        saved = question_write_service.save_ai_question(
            db,
            request.question,
            result.content,
            language=request.language,
            source=source,
            retrieved_question_ids=retrieved_ids,
            generation=GenerationMeta(
                model=result.model,
                prompt_version=prompts.ANSWER_PROMPT_VERSION,
                mode=mode,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
            ),
        )

    if saved is None:
        return None
    if user_id is not None:
        ask_history_service.record_ask(
            db, saved.id, user_id, request.language, cache_hit=False
        )
    return saved.id


def post_generation_tasks(question_id: int) -> None:
    """After the response is sent: translate, then (if enabled) AI-review.

    Each step is best effort and isolated; a failure in one must not stop
    the other, and neither can affect the already-sent answer.
    """
    # Stages here belong to no request; name them so the logs say so ([68]).
    with timing.request_path("background:post_generation"), background_session() as db:
        try:
            question_translation_service.translate_missing_languages(db, question_id)
        except Exception:
            logger.warning(
                "Background translation failed: question_id=%d",
                question_id,
                exc_info=True,
            )

        if settings.ai_review_enabled:
            question = db.get(Question, question_id)
            if question is not None:
                ai_review_service.review_question(db, question)
