"""The ask-AI use case: cache, generate, save, record ([59]).

Moved out of the router so the router only parses, authorises and calls
this. Behaviour is unchanged; see docs/api.md (AI) for the flow.
"""

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.core import prompts, timing
from physics_ai_tutor.core.config import settings
from physics_ai_tutor.database.session import async_background_session
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


async def _from_cache(
    db: AsyncSession, request: AskAiRequest, user_id: int | None
) -> AskAiResponse | None:
    """Cache tier 0: reuse an identical, non-rejected question's answer."""
    with timing.stage("ask_cache_lookup") as stage:
        cached = await question_read_service.async_find_cached_answer(
            db, request.question, request.language
        )
        stage.note(hit=cached is not None)

    if cached is None:
        return None
    if user_id is not None:
        await ask_history_service.async_record_ask(
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


async def _generate(db: AsyncSession, request: AskAiRequest):
    """Call the LLM in the requested mode; returns (result, ids, source, mode)."""
    if request.mode == "RAG":
        result, retrieved_ids = await rag_service.async_generate_rag_answer(
            db, request.question, request.retrieved_question_ids, request.language
        )
        return result, retrieved_ids, QuestionSource.RAG_RESULT, "RAG"
    result = await deepseek_service.async_generate_answer(
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


async def ask(
    db: AsyncSession,
    request: AskAiRequest,
    user_id: int | None,
    record_generation: Callable[[], Awaitable[None]],
    rate_limit_bucket: str,
) -> AskOutcome:
    """Answer one question; `record_generation` spends quota on a cache miss."""
    cached = await _from_cache(db, request, user_id)
    if cached is not None:
        return AskOutcome(cached)

    # Only a cache miss costs quota; it is about to trigger a generation.
    await record_generation()
    result, retrieved_ids, source, mode = await _generate(db, request)

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
    saved_id = await _save_answer(
        db, request, user_id, result, retrieved_ids, source, mode
    )
    return AskOutcome(
        AskAiResponse(
            answer=result.content,
            language=request.language,
            question_id=saved_id,
            status=QuestionStatus.UNREVIEWED if saved_id is not None else None,
        ),
        saved_question_id=saved_id,
    )


async def _save_answer(
    db: AsyncSession,
    request: AskAiRequest,
    user_id: int | None,
    result,
    retrieved_ids: list[int],
    source: QuestionSource,
    mode: str,
) -> int | None:
    """Store the answer as UNREVIEWED and record the ask; None if not saved."""
    with timing.stage("save_answer"):
        saved = await question_write_service.async_save_ai_question(
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
        await ask_history_service.async_record_ask(
            db, saved.id, user_id, request.language, cache_hit=False
        )
    return saved.id


async def post_generation_tasks(question_id: int) -> None:
    """After the response is sent: translate, then (if enabled) AI-review.

    Each step is best effort and isolated; a failure in one must not stop
    the other, and neither can affect the already-sent answer.
    """
    # Stages here belong to no request; name them so the logs say so ([68]).
    with timing.request_path("background:post_generation"):
        async with async_background_session() as db:
            try:
                await question_translation_service.async_translate_missing_languages(
                    db, question_id
                )
            except Exception:
                logger.warning(
                    "Background translation failed: question_id=%d",
                    question_id,
                    exc_info=True,
                )

            if settings.ai_review_enabled:
                question = await db.get(Question, question_id)
                if question is not None:
                    await ai_review_service.async_review_question(db, question)


@dataclass
class AskEvent:
    """One thing the client is told during a streamed ask ([71])."""

    kind: str
    text: str | None = None
    response: AskAiResponse | None = None
    detail: str | None = None


# Longest prefix that could still turn out to be the off-topic sentinel.
_SENTINEL = prompts.OFF_TOPIC_SENTINEL


def _sentinel_undecided(buffered: str) -> bool:
    """True while the buffer could still grow into the sentinel.

    The model marks a refusal with a leading `[OFF_TOPIC]`, which must
    never reach the student, so the opening of the stream is held back
    until it can be ruled in or out. A buffer that is a strict prefix of
    the sentinel is still undecided; anything else is decided.
    """
    stripped = buffered.lstrip()
    return len(stripped) < len(_SENTINEL) and _SENTINEL.startswith(stripped)


async def _stream_generation(
    db: AsyncSession, request: AskAiRequest
) -> AsyncIterator[str | tuple]:
    """Stream the LLM in the requested mode; last item is the metadata."""
    if request.mode == "RAG":
        async for piece in rag_service.async_stream_rag_answer(
            db, request.question, request.retrieved_question_ids, request.language
        ):
            if isinstance(piece, str):
                yield piece
            else:
                result, retrieved_ids = piece
                yield result, retrieved_ids, QuestionSource.RAG_RESULT, "RAG"
        return

    async for direct in deepseek_service.async_stream_answer(
        prompts.SYSTEM_PROMPTS[request.language], request.question
    ):
        if isinstance(direct, str):
            yield direct
        else:
            yield direct, [], QuestionSource.AI_GENERATED, "DIRECT"


async def ask_stream(
    db: AsyncSession,
    request: AskAiRequest,
    user_id: int | None,
    record_generation: Callable[[], Awaitable[None]],
    rate_limit_bucket: str,
    saved: dict,
) -> AsyncIterator[AskEvent]:
    """Answer one question as a stream of events ([71]).

    Same contract as `ask`: a cache hit costs no quota and no generation,
    a declined off-topic question is never saved, and the row written at
    the end is the one `ask` would have written. `saved` is filled with
    the new question id so the caller can schedule the post-generation
    tasks once the response has been sent.
    """
    cached = await _from_cache(db, request, user_id)
    if cached is not None:
        yield AskEvent("delta", text=cached.answer)
        yield AskEvent("done", response=cached)
        return

    # Only a cache miss costs quota; it is about to trigger a generation.
    await record_generation()

    buffered = ""
    opened = False
    declined = False
    metadata: tuple | None = None

    async for piece in _stream_generation(db, request):
        if not isinstance(piece, str):
            metadata = piece
            continue

        if declined:
            # Keep collecting the refusal, but send none of it: the
            # sentinel and the raw wording must not reach the student.
            buffered += piece
            continue

        if opened:
            yield AskEvent("delta", text=piece)
            continue

        buffered += piece
        if _sentinel_undecided(buffered):
            continue

        if buffered.lstrip().startswith(_SENTINEL):
            declined = True
            continue

        opened = True
        yield AskEvent("delta", text=buffered)

    if declined:
        message = _declined_message(buffered, request) or ""
        logger.info(
            "Ask AI declined off-topic question: bucket=%s mode=%s stream=1",
            rate_limit_bucket,
            request.mode or "DIRECT",
        )
        yield AskEvent("delta", text=message)
        yield AskEvent(
            "done",
            response=AskAiResponse(answer=message, language=request.language),
        )
        return

    if not opened and buffered:
        # The whole answer was shorter than the sentinel check needed.
        yield AskEvent("delta", text=buffered)

    if metadata is None:
        logger.warning("Streamed ask produced no result metadata")
        yield AskEvent("error", detail="Generation ended unexpectedly.")
        return

    result, retrieved_ids, source, mode = metadata

    logger.info(
        "Ask AI request answered: question_length=%d mode=%s language=%s stream=1",
        len(request.question),
        request.mode,
        request.language,
    )

    saved_id = await _save_answer(
        db, request, user_id, result, retrieved_ids, source, mode
    )
    saved["question_id"] = saved_id

    yield AskEvent(
        "done",
        response=AskAiResponse(
            answer=result.content,
            language=request.language,
            question_id=saved_id,
            status=QuestionStatus.UNREVIEWED if saved_id is not None else None,
        ),
    )
