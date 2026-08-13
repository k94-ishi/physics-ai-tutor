import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from physics_ai_tutor.api.dependencies import require_admin
from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.schemas.embedding import (
    SimilarQuestionRequest,
    SimilarQuestionResponse,
)
from physics_ai_tutor.schemas.question import (
    QuestionBulkCreate,
    QuestionCreate,
    QuestionListResponse,
    QuestionResponse,
    QuestionUpdate,
)
from physics_ai_tutor.schemas.token import JWTPayload
from physics_ai_tutor.services import question_service
from physics_ai_tutor.services.embedding_service import (
    search_similar_questions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get(
    "",
    response_model=QuestionListResponse,
)
def get_questions(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None, min_length=1, max_length=200),
    db: Session = Depends(get_db)
):

    return question_service.fetch_questions(
        db,
        page,
        size,
        keyword,
    )


@router.get(
    "/{question_id}",
    response_model=QuestionResponse,
)
def get_question(
    question_id: int,
    db: Session = Depends(get_db)
):
    question = question_service.fetch_question(
        db,
        question_id,
    )

    if question is None:
        raise HTTPException(
            status_code=404,
            detail="Question not found",
        )

    return question
    

@router.post(
    "",
    response_model=QuestionResponse,
    status_code=201,
)
def create_question(
    question: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: JWTPayload = Depends(require_admin),
):
    result = question_service.create_question(
        db,
        question,
    )
    logger.info(
        "Admin action: user_id=%s action=create_question question_id=%s",
        current_user.sub,
        result.id,
    )
    return result


@router.post(
    "/bulk",
    response_model=list[QuestionResponse],
    status_code=201,
)
def create_questions(
    questions: QuestionBulkCreate,
    db: Session = Depends(get_db),
    current_user: JWTPayload = Depends(require_admin),
):
    result = question_service.create_questions(
        db,
        questions,
    )
    logger.info(
        "Admin action: user_id=%s action=create_questions_bulk count=%d",
        current_user.sub,
        len(result),
    )
    return result


@router.delete(
    "/{question_id}",
    status_code=204
)
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: JWTPayload = Depends(require_admin),
):
    deleted = question_service.delete_question(
        db,
        question_id
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Question not found",
        )

    logger.info(
        "Admin action: user_id=%s action=delete_question question_id=%s",
        current_user.sub,
        question_id,
    )

    return Response(status_code=204)


@router.put(
    "/{question_id}",
    response_model=QuestionResponse,
)
def update_question(
    question_id: int,
    question: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: JWTPayload = Depends(require_admin),
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

    logger.info(
        "Admin action: user_id=%s action=update_question question_id=%s",
        current_user.sub,
        question_id,
    )

    return question


@router.post(
    "/search",
    response_model=list[SimilarQuestionResponse],
)
def search_questions(
    request: SimilarQuestionRequest,
    db: Session = Depends(get_db),
):
    return search_similar_questions(
        db=db,
        query=request.query,
        limit=request.limit,
    )