from openai import OpenAI

from physics_ai_tutor.core.config import settings

client = OpenAI(
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url,
)
