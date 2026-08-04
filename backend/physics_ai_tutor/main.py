from fastapi import FastAPI

from physics_ai_tutor.api.router import router
from physics_ai_tutor.core.config import settings

app = FastAPI(title="Physics AI Tutor", version="0.1.0")


app.include_router(router)

print(f"app_name: {settings.app_name}")
print(f"environment: {settings.environment}")
