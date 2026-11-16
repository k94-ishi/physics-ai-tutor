import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

from openai import OpenAIError

from physics_ai_tutor.core import timing
from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.deepseek import async_client
from physics_ai_tutor.core.exceptions import DeepSeekGenerationError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GenerationResult:
    """An answer plus the metadata needed to compare prompt versions later."""

    content: str
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None


def _result_from(response) -> GenerationResult:
    """Shape one completion into a GenerationResult."""
    content = response.choices[0].message.content or ""
    usage = getattr(response, "usage", None)
    # What the API actually served, which an alias may not name.
    model = getattr(response, "model", None) or settings.deepseek_chat_model

    logger.info(
        "DeepSeek answer generated: model=%s response_length=%d",
        model,
        len(content),
    )

    return GenerationResult(
        content=content,
        model=model,
        prompt_tokens=getattr(usage, "prompt_tokens", None),
        completion_tokens=getattr(usage, "completion_tokens", None),
    )


async def _async_request(
    system_prompt: str,
    user_prompt: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
):
    """One chat completion, with stage timing and a typed error."""
    logger.debug(
        "Requesting DeepSeek chat completion: prompt_length=%d", len(user_prompt)
    )

    extra: dict = {}
    if temperature is not None:
        # Evaluation runs pin temperature for reproducibility.
        extra["temperature"] = temperature

    try:
        # The dominant stage of any uncached answer ([68]).
        with timing.stage("deepseek_chat", prompt_length=len(user_prompt)) as stage:
            response = await async_client.chat.completions.create(
                model=settings.deepseek_chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens or settings.deepseek_max_tokens,
                **extra,
            )
            usage = getattr(response, "usage", None)
            stage.note(
                completion_tokens=getattr(usage, "completion_tokens", None),
            )
            return response
    except OpenAIError as exc:
        logger.warning("DeepSeek chat completion failed: %s", type(exc).__name__)
        raise DeepSeekGenerationError(
            "Failed to generate a response via the DeepSeek API."
        ) from exc


async def async_chat_completion(system_prompt: str, user_prompt: str) -> str:
    """Plain text completion for callers that need no usage metadata."""
    response = await _async_request(system_prompt, user_prompt)
    content = response.choices[0].message.content

    logger.info(
        "DeepSeek chat completion succeeded: model=%s response_length=%d",
        settings.deepseek_chat_model,
        len(content or ""),
    )

    return content or ""


async def async_generate_answer(
    system_prompt: str,
    user_prompt: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> GenerationResult:
    """Answer generation; records the model and token usage for the row."""
    response = await _async_request(system_prompt, user_prompt, temperature, max_tokens)

    return _result_from(response)


async def async_stream_answer(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int | None = None,
) -> AsyncIterator[str | GenerationResult]:
    """Yield the answer in pieces, then one GenerationResult last ([71]).

    Text deltas come through as `str`; the final item is the
    `GenerationResult` the non-streaming path would have returned, so a
    caller can save the same row. Usage arrives in a final usage-only
    chunk (`stream_options`), which DeepSeek may omit - the row then
    carries null token counts rather than wrong ones.
    """
    logger.debug(
        "Streaming DeepSeek chat completion: prompt_length=%d", len(user_prompt)
    )

    pieces: list[str] = []
    model: str | None = None
    usage = None

    try:
        with timing.stage("deepseek_stream", prompt_length=len(user_prompt)) as stage:
            stream = await async_client.chat.completions.create(
                model=settings.deepseek_chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens or settings.deepseek_max_tokens,
                stream=True,
                stream_options={"include_usage": True},
            )

            async for chunk in stream:
                model = getattr(chunk, "model", None) or model
                usage = getattr(chunk, "usage", None) or usage

                # A usage-only chunk carries no choices.
                if not chunk.choices:
                    continue

                delta = getattr(chunk.choices[0].delta, "content", None)
                if delta:
                    pieces.append(delta)
                    yield delta

            stage.note(
                chunks=len(pieces),
                completion_tokens=getattr(usage, "completion_tokens", None),
            )
    except OpenAIError as exc:
        logger.warning("DeepSeek streaming failed: %s", type(exc).__name__)
        raise DeepSeekGenerationError(
            "Failed to generate a response via the DeepSeek API."
        ) from exc

    content = "".join(pieces)

    logger.info(
        "DeepSeek answer streamed: model=%s response_length=%d chunks=%d",
        model or settings.deepseek_chat_model,
        len(content),
        len(pieces),
    )

    yield GenerationResult(
        content=content,
        model=model or settings.deepseek_chat_model,
        prompt_tokens=getattr(usage, "prompt_tokens", None),
        completion_tokens=getattr(usage, "completion_tokens", None),
    )
