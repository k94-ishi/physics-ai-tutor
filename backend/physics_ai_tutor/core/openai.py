"""OpenAI client for embeddings (async only since [108])."""

from openai import AsyncOpenAI

from physics_ai_tutor.core.config import settings

# Without this the SDK would wait its default 10 minutes on a hung
# connection, holding a request for the whole time.
REQUEST_TIMEOUT_SECONDS = 30.0

async_client = AsyncOpenAI(
    api_key=settings.openai_api_key,
    timeout=REQUEST_TIMEOUT_SECONDS,
)
