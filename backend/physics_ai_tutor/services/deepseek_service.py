import logging
from dataclasses import dataclass

from openai import OpenAIError

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.deepseek import client
from physics_ai_tutor.core.exceptions import DeepSeekGenerationError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GenerationResult:
    """An answer plus the metadata needed to compare prompt versions later."""

    content: str
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None


def _request(system_prompt: str, user_prompt: str, temperature: float | None = None):
    logger.debug(
        "Requesting DeepSeek chat completion: prompt_length=%d", len(user_prompt)
    )

    extra: dict = {}
    if temperature is not None:
        # Evaluation runs pin temperature for reproducibility.
        extra["temperature"] = temperature

    try:
        return client.chat.completions.create(
            model=settings.deepseek_chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=settings.deepseek_max_tokens,
            **extra,
        )
    except OpenAIError as exc:
        logger.warning("DeepSeek chat completion failed: %s", type(exc).__name__)
        raise DeepSeekGenerationError(
            "Failed to generate a response via the DeepSeek API."
        ) from exc


def chat_completion(system_prompt: str, user_prompt: str) -> str:
    """Plain text completion for callers that need no usage metadata."""
    response = _request(system_prompt, user_prompt)
    content = response.choices[0].message.content

    logger.info(
        "DeepSeek chat completion succeeded: model=%s response_length=%d",
        settings.deepseek_chat_model,
        len(content or ""),
    )

    return content or ""


def generate_answer(
    system_prompt: str, user_prompt: str, temperature: float | None = None
) -> GenerationResult:
    """Answer generation; records the model and token usage for the row."""
    response = _request(system_prompt, user_prompt, temperature)
    content = response.choices[0].message.content or ""
    usage = getattr(response, "usage", None)

    logger.info(
        "DeepSeek answer generated: model=%s response_length=%d",
        settings.deepseek_chat_model,
        len(content),
    )

    return GenerationResult(
        content=content,
        model=settings.deepseek_chat_model,
        prompt_tokens=getattr(usage, "prompt_tokens", None),
        completion_tokens=getattr(usage, "completion_tokens", None),
    )
