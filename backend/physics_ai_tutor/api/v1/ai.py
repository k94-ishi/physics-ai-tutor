import logging

from fastapi import APIRouter

from physics_ai_tutor.schemas.ai import AskAiRequest, AskAiResponse
from physics_ai_tutor.services import deepseek_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])

_SYSTEM_PROMPT = (
    "あなたは日本の高校物理を教える親切なAIチューターです。"
    "生徒からの質問に、簡潔かつ正確な日本語で答えてください。"
)


@router.post("/ask", response_model=AskAiResponse)
def ask_ai(request: AskAiRequest):
    answer = deepseek_service.chat_completion(_SYSTEM_PROMPT, request.question)

    logger.info("Ask AI request answered: question_length=%d", len(request.question))

    return AskAiResponse(answer=answer)
