import json
import logging

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from sqlalchemy.orm import Session

from physics_ai_tutor.api.dependencies import get_current_user_optional, require_admin
from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.schemas.bulk import (
    BulkDeleteRequest,
    BulkDeleteResponse,
    BulkReviewRequest,
    BulkReviewResponse,
)
from physics_ai_tutor.schemas.concept import (
    ConceptExtractionBatchResponse,
    ConceptExtractionRequest,
)
from physics_ai_tutor.schemas.embedding import (
    SimilarQuestionRequest,
    SimilarQuestionResponse,
)
from physics_ai_tutor.schemas.question import (
    QuestionCreate,
    QuestionImportResponse,
    QuestionListResponse,
    QuestionResponse,
    QuestionSource,
    QuestionStatus,
    QuestionUpdate,
)
from physics_ai_tutor.schemas.question_review import (
    QuestionReviewCreate,
    QuestionReviewResponse,
)
from physics_ai_tutor.schemas.token import JWTPayload, UserRole
from physics_ai_tutor.services import question_service, recommendation_service
from physics_ai_tutor.services.embedding_service import (
    search_similar_questions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/questions", tags=["questions"])


def _is_admin(current_user: JWTPayload | None) -> bool:
    return current_user is not None and current_user.role == UserRole.ADMIN


@router.get(
    "",
    response_model=QuestionListResponse,
)
def get_questions(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None, min_length=1, max_length=200),
    status: QuestionStatus | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: JWTPayload | None = Depends(get_current_user_optional),
):
    is_admin = _is_admin(current_user)

    return question_service.fetch_questions(
        db,
        page,
        size,
        keyword,
        status=status,
        exclude_status=None if is_admin else QuestionStatus.REJECTED,
    )


@router.get(
    "/{question_id}",
    response_model=QuestionResponse,
)
def get_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: JWTPayload | None = Depends(get_current_user_optional),
):
    is_admin = _is_admin(current_user)

    question = question_service.fetch_question(
        db,
        question_id,
        exclude_status=None if is_admin else QuestionStatus.REJECTED,
    )

    if question is None:
        raise HTTPException(
            status_code=404,
            detail="Question not found",
        )

    return question


@router.get(
    "/{question_id}/related",
    response_model=list[QuestionResponse],
)
def get_related_questions(
    question_id: int,
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    return recommendation_service.get_related_questions(db, question_id, limit=limit)


@router.get(
    "/{question_id}/reviews",
    response_model=list[QuestionReviewResponse],
)
def get_question_reviews(
    question_id: int,
    db: Session = Depends(get_db),
    _: JWTPayload = Depends(require_admin),
):
    return question_service.fetch_question_reviews(db, question_id)


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
        status=QuestionStatus.APPROVED,
        source=QuestionSource.MANUAL,
    )
    logger.info(
        "Admin action: user_id=%s action=create_question question_id=%s",
        current_user.sub,
        result.id,
    )
    return result


@router.post(
    "/bulk-delete",
    response_model=BulkDeleteResponse,
)
def bulk_delete_questions(
    data: BulkDeleteRequest,
    db: Session = Depends(get_db),
    current_user: JWTPayload = Depends(require_admin),
):
    deleted_count, not_found_ids = question_service.bulk_delete_questions(
        db, data.question_ids
    )

    logger.info(
        "Admin action: user_id=%s action=bulk_delete_questions "
        "deleted_count=%d not_found_count=%d",
        current_user.sub,
        deleted_count,
        len(not_found_ids),
    )

    return BulkDeleteResponse(deleted_count=deleted_count, not_found_ids=not_found_ids)


@router.post(
    "/bulk-review",
    response_model=BulkReviewResponse,
)
def bulk_review_questions(
    data: BulkReviewRequest,
    db: Session = Depends(get_db),
    current_user: JWTPayload = Depends(require_admin),
):
    updated_questions, not_found_ids = question_service.bulk_review_questions(
        db,
        data.question_ids,
        action=data.action,
        reviewer_id=int(current_user.sub),
        comment=data.comment,
    )

    logger.info(
        "Admin action: user_id=%s action=bulk_review_questions "
        "review_action=%s updated_count=%d not_found_count=%d",
        current_user.sub,
        data.action,
        len(updated_questions),
        len(not_found_ids),
    )

    return BulkReviewResponse(questions=updated_questions, not_found_ids=not_found_ids)


@router.post(
    "/concepts/extract",
    response_model=ConceptExtractionBatchResponse,
)
def extract_concepts(
    data: ConceptExtractionRequest,
    db: Session = Depends(get_db),
    current_user: JWTPayload = Depends(require_admin),
):
    results = question_service.reextract_concepts_for_questions(
        db, data.question_ids
    )

    logger.info(
        "Admin action: user_id=%s action=extract_concepts "
        "requested_count=%d success_count=%d",
        current_user.sub,
        len(data.question_ids),
        sum(1 for r in results if r.success),
    )

    return ConceptExtractionBatchResponse(results=results)


@router.post(
    "/import",
    response_model=QuestionImportResponse,
    status_code=201,
)
def import_questions(
    file: UploadFile = File(...),
    source: QuestionSource = Form(default=QuestionSource.AI_GENERATED),
    status: QuestionStatus = Form(default=QuestionStatus.UNREVIEWED),
    db: Session = Depends(get_db),
    current_user: JWTPayload = Depends(require_admin),
):
    raw_lines = file.file.read().decode("utf-8").splitlines()

    rows: list[QuestionCreate] = []
    errors: list[str] = []

    for line_number, raw_line in enumerate(raw_lines, start=1):
        line = raw_line.strip()

        if not line:
            continue

        try:
            data = json.loads(line)
            rows.append(QuestionCreate(**data))
        except Exception as exc:
            errors.append(f"line {line_number}: {exc}")

    if errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "Invalid JSONL file", "errors": errors},
        )

    if not rows:
        raise HTTPException(status_code=422, detail="File contains no questions")

    created = question_service.import_questions_from_jsonl(
        db,
        rows,
        status=status,
        source=source,
    )

    logger.info(
        "Admin action: user_id=%s action=import_questions count=%d source=%s status=%s",
        current_user.sub,
        len(created),
        source,
        status,
    )

    return QuestionImportResponse(created_count=len(created), questions=created)


@router.post(
    "/{question_id}/review",
    response_model=QuestionResponse,
)
def review_question(
    question_id: int,
    data: QuestionReviewCreate,
    db: Session = Depends(get_db),
    current_user: JWTPayload = Depends(require_admin),
):
    result = question_service.review_question(
        db,
        question_id,
        action=data.action,
        reviewer_id=int(current_user.sub),
        question=data.question,
        answer=data.answer,
        comment=data.comment,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Question not found",
        )

    logger.info(
        "Admin action: user_id=%s action=review_question "
        "question_id=%s review_action=%s",
        current_user.sub,
        question_id,
        data.action,
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
