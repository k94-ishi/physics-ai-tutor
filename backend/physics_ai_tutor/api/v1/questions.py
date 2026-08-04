from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.schemas.question import QuestionResponse
from physics_ai_tutor.services import question_service

router = APIRouter()


@router.get(
    "/questions",
    response_model=list[QuestionResponse],
)
def get_questions(db: Session = Depends(get_db)):
    
    return question_service.fetch_questions(db)
