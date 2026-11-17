import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.api.dependencies import (
    get_current_user_optional,
    is_admin,
)
from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.schemas.embedding import (
    SimilarQuestionRequest,
    SimilarQuestionResponse,
)
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.question import (
    AiVerdictFilter,
    PrerequisitesResponse,
    QuestionFilters,
    QuestionListResponse,
    QuestionResponse,
    QuestionSort,
    QuestionStatus,
)
from physics_ai_tutor.schemas.token import JWTPayload
from physics_ai_tutor.services import (
    background_translation_service,
    concept_sense_service,
    prerequisite_service,
    question_presentation_service,
    question_read_service,
    recommendation_service,
)
from physics_ai_tutor.services.embedding_service import (
    search_similar_questions,
)
from physics_ai_tutor.services.response_language import (
    ResponseLanguage,
    TranslationNeeds,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/questions", tags=["questions"])


# Statuses that must never be shown to non-admin callers.
PUBLIC_HIDDEN_STATUSES: list[str] = [
    QuestionStatus.UNREVIEWED,
    QuestionStatus.REJECTED,
]


# Admin id search ([31]): at most this many ids per request.
MAX_ID_FILTER = 100


def _parse_ids(raw: str | None) -> list[int] | None:
    """Parse `ids=54,848`; None means no filter, [] means match nothing.

    An unparseable or over-long list filters everything out rather than
    silently listing the whole queue, which would look like a search hit.
    """
    if raw is None:
        return None

    parts = [part.strip() for part in raw.split(",") if part.strip()]
    if not parts or len(parts) > MAX_ID_FILTER:
        raise HTTPException(
            status_code=422,
            detail=f"ids must hold 1 to {MAX_ID_FILTER} question ids",
        )

    try:
        return [int(part) for part in parts]
    except ValueError:
        raise HTTPException(status_code=422, detail="ids must be integers") from None


def _hidden_statuses_for(current_user: JWTPayload | None) -> list[str] | None:
    # Admins see everything; everyone else only sees approved content.
    return None if is_admin(current_user) else PUBLIC_HIDDEN_STATUSES


def _response_language(
    lang: Language, current_user: JWTPayload | None
) -> ResponseLanguage:
    # Students never read the other language; admins get the fallback ([53]).
    return ResponseLanguage.for_caller(lang, admin=is_admin(current_user))


async def _queue_translations(
    background_tasks: BackgroundTasks,
    db: AsyncSession,
    needs: TranslationNeeds,
    language: Language,
) -> None:
    """Translate what a strict response left out, once, after the response.

    Queued unconditionally: the task claims each row in the database and
    drops the ones another worker already holds ([75]). Deciding here
    would only be right for this process.
    """
    if needs.question_ids:
        background_tasks.add_task(
            background_translation_service.translate_missing, needs.question_ids
        )
    if not needs.concept_question_ids:
        return
    missing = await concept_sense_service.concept_ids_missing_name(
        db, needs.concept_question_ids, language.value
    )
    if missing:
        background_tasks.add_task(
            background_translation_service.translate_concept_names, missing
        )


@router.get(
    "",
    response_model=QuestionListResponse,
)
async def get_questions(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=30, ge=1, le=120),
    keyword: str | None = Query(default=None, min_length=1, max_length=200),
    status: QuestionStatus | None = Query(default=None),
    search_question: bool = Query(default=True),
    search_answer: bool = Query(default=True),
    lang: Language = Query(default=Language.JA),
    sort: QuestionSort | None = Query(default=None),
    ai_verdict: AiVerdictFilter | None = Query(default=None),
    ids: str | None = Query(
        default=None,
        max_length=800,
        description="Admin only: comma-separated question ids, at most 100.",
    ),
    concept: str | None = Query(
        default=None,
        min_length=1,
        max_length=255,
        description="Questions linked to any sense having this word (either language).",
    ),
    concept_id: int | None = Query(
        default=None, ge=1, description="Questions linked to exactly this sense."
    ),
    db: AsyncSession = Depends(get_db),
    current_user: JWTPayload | None = Depends(get_current_user_optional),
):
    # AI-verdict sorting and filtering and the id list are admin tools.
    admin = is_admin(current_user)
    filters = QuestionFilters(
        keyword=keyword,
        status=status,
        exclude_statuses=_hidden_statuses_for(current_user),
        search_question=search_question,
        search_answer=search_answer,
        ai_verdict=ai_verdict.value if ai_verdict and admin else None,
        ids=_parse_ids(ids) if admin else None,
        concept=concept,
        concept_id=concept_id,
    )
    return await question_read_service.fetch_questions(
        db,
        page,
        size,
        filters,
        language=_response_language(lang, current_user),
        sort=sort.value if sort and admin else None,
        include_admin_fields=admin,
    )


@router.get(
    "/exact-match",
    response_model=QuestionResponse,
)
async def get_exact_match_question(
    question: str = Query(..., min_length=1, max_length=200),
    lang: Language = Query(default=Language.JA),
    db: AsyncSession = Depends(get_db),
    current_user: JWTPayload | None = Depends(get_current_user_optional),
):
    result = await question_read_service.fetch_question_by_exact_text(
        db,
        question,
        exclude_statuses=_hidden_statuses_for(current_user),
        language=_response_language(lang, current_user),
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Question not found",
        )

    return result


@router.get(
    "/{question_id}",
    response_model=QuestionResponse,
)
async def get_question(
    background_tasks: BackgroundTasks,
    question_id: int,
    lang: Language = Query(default=Language.JA),
    db: AsyncSession = Depends(get_db),
    current_user: JWTPayload | None = Depends(get_current_user_optional),
):
    # Rows approved before translation existed are filled on first view.
    question, needs = await question_read_service.fetch_question(
        db,
        question_id,
        exclude_statuses=_hidden_statuses_for(current_user),
        language=_response_language(lang, current_user),
    )

    if question is None:
        raise HTTPException(
            status_code=404,
            detail="Question not found",
        )

    if is_admin(current_user):
        question_presentation_service.attach_generation_meta([question])
        await question_presentation_service.attach_ai_reviews(db, [question])
    await _queue_translations(background_tasks, db, needs, lang)

    return question


@router.get(
    "/{question_id}/related",
    response_model=list[QuestionResponse],
)
async def get_related_questions(
    background_tasks: BackgroundTasks,
    question_id: int,
    limit: int = Query(default=5, ge=1, le=20),
    lang: Language = Query(default=Language.JA),
    db: AsyncSession = Depends(get_db),
    current_user: JWTPayload | None = Depends(get_current_user_optional),
):
    related = await recommendation_service.get_related_questions(
        db,
        question_id,
        limit=limit,
        exclude_statuses=(
            [QuestionStatus.REJECTED]
            if is_admin(current_user)
            else PUBLIC_HIDDEN_STATUSES
        ),
        language=_response_language(lang, current_user),
    )
    await _queue_translations(background_tasks, db, related.needs, lang)
    return related.items


@router.get(
    "/{question_id}/prerequisites",
    response_model=PrerequisitesResponse,
)
async def get_prerequisites(
    background_tasks: BackgroundTasks,
    question_id: int,
    limit: int = Query(default=5, ge=1, le=20),
    lang: Language = Query(default=Language.JA),
    db: AsyncSession = Depends(get_db),
    current_user: JWTPayload | None = Depends(get_current_user_optional),
):
    """Defining QAs for the concepts this QA leans on ([38]).

    Students climb down, so only APPROVED rows ever appear, for admins
    too; concepts with no usable definer come back as gaps.
    """
    result = await prerequisite_service.get_prerequisites(
        db,
        question_id,
        limit=limit,
        language=_response_language(lang, current_user),
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Question not found")
    await _queue_translations(background_tasks, db, result.needs, lang)
    return result.response


@router.post(
    "/search",
    response_model=list[SimilarQuestionResponse],
)
async def search_questions(
    request: SimilarQuestionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: JWTPayload | None = Depends(get_current_user_optional),
):
    # Converted in [70]: this is the read that costs an OpenAI call.
    return await search_similar_questions(
        db=db,
        query=request.query,
        limit=request.limit,
        exclude_statuses=_hidden_statuses_for(current_user),
        language=request.language,
    )
