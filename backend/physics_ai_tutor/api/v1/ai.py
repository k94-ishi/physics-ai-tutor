import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.schemas.ai import AskAiRequest, AskAiResponse
from physics_ai_tutor.services import deepseek_service, question_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])

_SYSTEM_PROMPT = (
    "あなたは日本の高校物理を教える先生です。"
    "生徒からの質問に、丁寧、簡潔かつ正確な日本語で答えること"
    "物理や数学が苦手な生徒の質問だと想定し、わかりやすく親切に説明してください。"
    "文字式を使う場合は各文字の意味を省略せず説明すること。"
    "「いい質問ですね」のような前置きはせず、回答から始めてください。"
    "「他に質問はないですか？」のような対話を促す呼びかけはしない。"
    "数式を用いる場合は$で囲む形式(例: $v = at$)を用い、ベクトルには\\vec{}を使うこと。"
    "Markdown記法では、書式記号の直後・直前には必要なら半角スペースを入れてください。"
    "図解が有効な場合はMermaid形式のコードブロックを使っても構いません。"
)


@router.post("/ask", response_model=AskAiResponse)
def ask_ai(request: AskAiRequest, db: Session = Depends(get_db)):
    answer = deepseek_service.chat_completion(_SYSTEM_PROMPT, request.question)

    logger.info("Ask AI request answered: question_length=%d", len(request.question))

    question_service.save_ai_question(db, request.question, answer)

    return AskAiResponse(answer=answer)
