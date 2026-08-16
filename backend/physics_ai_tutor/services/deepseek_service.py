import logging

from openai import OpenAIError

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.deepseek import client
from physics_ai_tutor.core.exceptions import DeepSeekGenerationError

logger = logging.getLogger(__name__)


def chat_completion(system_prompt: str, user_prompt: str) -> str:
    logger.debug(
        "Requesting DeepSeek chat completion: prompt_length=%d", len(user_prompt)
    )

    try:
        response = client.chat.completions.create(
            model=settings.deepseek_chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=settings.deepseek_max_tokens,
        )
    except OpenAIError as exc:
        logger.warning("DeepSeek chat completion failed: %s", type(exc).__name__)
        raise DeepSeekGenerationError(
            "Failed to generate a response via the DeepSeek API."
        ) from exc

    content = response.choices[0].message.content

    logger.info(
        "DeepSeek chat completion succeeded: model=%s response_length=%d",
        settings.deepseek_chat_model, len(content or ""),
    )

    return content or ""
