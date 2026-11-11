"""OpenAI clients for embeddings.

Both a sync and an async client while Track F ([67]) converts the app:
converted code uses `async_client`, the rest keeps `client`. [73] removes
the sync one.
"""

from openai import AsyncOpenAI, OpenAI

from physics_ai_tutor.core.config import settings

# Without this the SDK would wait its default 10 minutes on a hung
# connection, holding a thread (or a request) for the whole time.
REQUEST_TIMEOUT_SECONDS = 30.0

client = OpenAI(
    api_key=settings.openai_api_key,
    timeout=REQUEST_TIMEOUT_SECONDS,
)

async_client = AsyncOpenAI(
    api_key=settings.openai_api_key,
    timeout=REQUEST_TIMEOUT_SECONDS,
)
