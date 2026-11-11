"""DeepSeek clients for answer generation, review and translation.

Both a sync and an async client while Track F ([67]) converts the app:
converted code uses `async_client`, the rest keeps `client`. [73] removes
the sync one.
"""

from openai import AsyncOpenAI, OpenAI

from physics_ai_tutor.core.config import settings

# Generous, because a long answer legitimately takes tens of seconds, but
# finite: the SDK's default is 10 minutes, which is long enough to look
# like a hang.
REQUEST_TIMEOUT_SECONDS = 180.0

client = OpenAI(
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url,
    timeout=REQUEST_TIMEOUT_SECONDS,
)

async_client = AsyncOpenAI(
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url,
    timeout=REQUEST_TIMEOUT_SECONDS,
)
