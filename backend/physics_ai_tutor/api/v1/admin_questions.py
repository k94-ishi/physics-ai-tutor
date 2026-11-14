"""Admin question endpoints: create, edit, review, import, bulk actions ([60]).

Same `/questions` prefix as the public router; registered after it.
"""

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
from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.api.dependencies import (
    require_admin,
)
from physics_ai_tutor.database.dependency import get_async_db
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
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.question import (
    QuestionCreate,
    QuestionImportResponse,
    QuestionResponse,
    QuestionSource,
    QuestionStatus,
    QuestionUpdate,
    TranslationBatchResponse,
    TranslationResult,
)
from physics_ai_tutor.schemas.question_review import (
    QuestionReviewCreate,
    QuestionReviewResponse,
)
from physics_ai_tutor.schemas.token import JWTPayload
from physics_ai_tutor.services import (
    question_review_service,
    question_translation_service,
    question_write_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get(
    "/{question_id}/reviews",
    response_model=list[QuestionReviewResponse],
)
async def get_question_reviews(
    question_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: JWTPayload = Depends(require_admin),
):
    return await question_review_service.fetch_question_reviews(db, question_id)


@router.post(
    "",
    response_model=QuestionResponse,
    status_code=201,
)
async def create_question(
    question: QuestionCreate,
    lang: Language = Query(default=Language.JA),
    db: AsyncSession = Depends(get_async_db),
    current_user: JWTPayload = Depends(require_admin),
):
    result = await question_write_service.create_question(
        db,
        question,
        status=QuestionStatus.APPROVED,
        source=QuestionSource.MANUAL,
        language=lang,
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
async def bulk_delete_questions(
    data: BulkDeleteRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: JWTPayload = Depends(require_admin),
):
    deleted_count, not_found_ids = await question_write_service.bulk_delete_questions(
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
async def bulk_review_questions(
    data: BulkReviewRequest,
    lang: Language = Query(default=Language.JA),
    db: AsyncSession = Depends(get_async_db),
    current_user: JWTPayload = Depends(require_admin),
):
    (
        updated_questions,
        not_found_ids,
    ) = await question_review_service.bulk_review_questions(
        db,
        data.question_ids,
        action=data.action,
        reviewer_id=int(current_user.sub),
        reason=data.reason,
        comment=data.comment,
        response_language=lang,
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
async def extract_concepts(
    data: ConceptExtractionRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: JWTPayload = Depends(require_admin),
):
    results = await question_write_service.reextract_concepts_for_questions(
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
    "/translate",
    response_model=TranslationBatchResponse,
)
async def translate_questions(
    data: BulkDeleteRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: JWTPayload = Depends(require_admin),
):
    """Fill missing languages of the given questions by machine translation."""
    results = []
    for question_id in data.question_ids:
        try:
            filled = (
                await question_translation_service.async_translate_missing_languages(
                    db, question_id
                )
            )
        except Exception:
            logger.warning(
                "Translation failed: question_id=%d", question_id, exc_info=True
            )
            results.append(TranslationResult(question_id=question_id, success=False))
            continue

        for language in filled:
            results.append(
                TranslationResult(
                    question_id=question_id, success=True, language=language
                )
            )
        if not filled:
            results.append(TranslationResult(question_id=question_id, success=False))

    logger.info(
        "Admin action: user_id=%s action=translate_questions requested_count=%d",
        current_user.sub,
        len(data.question_ids),
    )

    return TranslationBatchResponse(results=results)


@router.post(
    "/import",
    response_model=QuestionImportResponse,
    status_code=201,
)
async def import_questions(
    file: UploadFile = File(...),
    source: QuestionSource = Form(default=QuestionSource.AI_GENERATED),
    status: QuestionStatus = Form(default=QuestionStatus.UNREVIEWED),
    language: Language = Form(default=Language.JA),
    db: AsyncSession = Depends(get_async_db),
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
            # Legacy rows carry no language; use the form's default.
            data.setdefault("language", language.value)
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

    created = await question_write_service.import_questions_from_jsonl(
        db,
        rows,
        status=status,
        source=source,
        language=language,
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
async def review_question(
    question_id: int,
    data: QuestionReviewCreate,
    lang: Language = Query(default=Language.JA),
    db: AsyncSession = Depends(get_async_db),
    current_user: JWTPayload = Depends(require_admin),
):
    result = await question_review_service.review_question(
        db,
        question_id,
        action=data.action,
        reviewer_id=int(current_user.sub),
        question=data.question,
        answer=data.answer,
        reason=data.reason,
        comment=data.comment,
        language=data.language,
        response_language=lang,
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


@router.delete("/{question_id}", status_code=204)
async def delete_question(
    question_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: JWTPayload = Depends(require_admin),
):
    deleted = await question_write_service.delete_question(db, question_id)

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
async def update_question(
    question_id: int,
    question: QuestionUpdate,
    lang: Language = Query(default=Language.JA),
    db: AsyncSession = Depends(get_async_db),
    current_user: JWTPayload = Depends(require_admin),
):
    question = await question_write_service.update_question(
        db,
        question_id,
        question,
        language=lang,
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
