from openai import OpenAI

from physics_ai_tutor import settings

client = OpenAI(
    api_key=settings.openai_api_key,
)