from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.schemas.question import (
    QuestionBulkCreate,
    QuestionCreate,
    QuestionResponse,
    QuestionUpdate,
)
from physics_ai_tutor.services import question_service

router = APIRouter()


@router.get(
    "/questions",
    response_model=list[QuestionResponse],
)
def get_questions(db: Session = Depends(get_db)):
    
    return question_service.fetch_questions(db)


@router.get(
    "/questions/{question_id}",
    response_model=QuestionResponse,
)
def get_question(
    question_id: int,
    db: Session = Depends(get_db)
):
    return question_service.fetch_question(
        db,
        question_id,
    )
    

@router.post(
    "/questions",
    response_model=QuestionResponse,
)
def create_question(
    question: QuestionCreate,
    db: Session = Depends(get_db)
):
    return question_service.create_question(
        db,
        question,
    )


@router.post(
    "/questions/bulk",
    response_model=list[QuestionResponse],
)
def create_questions(
    questions: QuestionBulkCreate,
    db: Session = Depends(get_db),
):
    return question_service.create_questions(
        db,
        questions,
    )


@router.delete(
    "/questions/{question_id}",
    status_code=204
)
def delete_question(
    question_id: int,
    db: Session = Depends(get_db)
):
    question_service.delete_question(
        db,
        question_id
    )

    return Response(status_code=204)


@router.put(
    "/questions/{question_id}",
    response_model=QuestionResponse,
)
def update_question(
    question_id: int,
    question: QuestionUpdate,
    db: Session = Depends(get_db),
):
    question = question_service.update_question(
        db,
        question_id,
        question,
    )
    
    if question is None:
        raise HTTPException(
            status_code=404,
            detail="Question not found",
        )