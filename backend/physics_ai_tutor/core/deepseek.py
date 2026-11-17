"""DeepSeek client for generation, review and translation (async only, [108])."""

from openai import AsyncOpenAI

from physics_ai_tutor.core.config import settings

# Generous, because a long answer legitimately takes tens of seconds, but
# finite: the SDK's default is 10 minutes, which is long enough to look
# like a hang.
REQUEST_TIMEOUT_SECONDS = 180.0

async_client = AsyncOpenAI(
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url,
    timeout=REQUEST_TIMEOUT_SECONDS,
)
