import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from physics_ai_tutor.api.dependencies import enforce_ai_ask_rate_limit
from physics_ai_tutor.core import prompts
from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.schemas.ai import AskAiRequest, AskAiResponse
from physics_ai_tutor.schemas.question import QuestionSource
from physics_ai_tutor.services import deepseek_service, question_service, rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post(
    "/ask",
    response_model=AskAiResponse,
    dependencies=[Depends(enforce_ai_ask_rate_limit)],
)
def ask_ai(request: AskAiRequest, db: Session = Depends(get_db)):
    if request.mode == "RAG":
        answer, retrieved_ids = rag_service.generate_rag_answer(
            db, request.question, request.retrieved_question_ids
        )
        source = QuestionSource.RAG_RESULT
    else:
        answer = deepseek_service.chat_completion(
            prompts.SYSTEM_PROMPT, request.question
        )
        retrieved_ids = []
        source = QuestionSource.AI_GENERATED

    logger.info(
        "Ask AI request answered: question_length=%d mode=%s",
        len(request.question),
        request.mode,
    )

    question_service.save_ai_question(
        db,
        request.question,
        answer,
        source=source,
        retrieved_question_ids=retrieved_ids,
    )

    return AskAiResponse(answer=answer)
