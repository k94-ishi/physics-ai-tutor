import logging
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from physics_ai_tutor.api.dependencies import (
    get_current_user_optional,
    is_admin,
    require_admin,
)
from physics_ai_tutor.database.dependency import get_async_db, get_db
from physics_ai_tutor.schemas.concept import (
    AdminConceptListResponse,
    AdminConceptResponse,
    ConceptGlossUpdate,
    ConceptMergeRequest,
    ConceptSearchItem,
    ConceptSplitRequest,
    ConceptTermCreate,
    ConceptTermUpdate,
)
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.token import JWTPayload
from physics_ai_tutor.services import concept_sense_service
from physics_ai_tutor.services.concept_sense_service import (
    ConceptNotFoundError,
    DuplicateTermError,
    NewTerm,
    TermNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/concepts", tags=["concepts"])
admin_router = APIRouter(prefix="/admin/concepts", tags=["admin"])


@router.get("", response_model=list[ConceptSearchItem])
async def search_concepts(
    q: str = Query(default="", max_length=100),
    lang: Language = Query(default=Language.JA),
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db),
    current_user: JWTPayload | None = Depends(get_current_user_optional),
):
    """Concept senses by any of their words, in either language ([55])."""
    return await concept_sense_service.search(
        db, q, lang.value, public=not is_admin(current_user), limit=limit
    )


# --- admin editor -------------------------------------------------------------


@contextmanager
def _http_errors() -> Iterator[None]:
    """Map the editor's domain errors to HTTP responses."""
    try:
        yield
    except ConceptNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Concept not found") from exc
    except TermNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Term not found") from exc
    except DuplicateTermError as exc:
        raise HTTPException(
            status_code=409, detail="The concept already has this word"
        ) from exc


def _detail(db: Session, concept_id: int, lang: Language) -> AdminConceptResponse:
    item = concept_sense_service.detail_for_admin(db, concept_id, lang.value)
    if item is None:
        raise HTTPException(status_code=404, detail="Concept not found")
    return item


@admin_router.get("", response_model=AdminConceptListResponse)
def list_concepts(
    q: str = Query(default="", max_length=100),
    review_filter: str = Query(default="all", pattern="^(all|review|shared)$"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    _: JWTPayload = Depends(require_admin),
):
    return concept_sense_service.list_for_admin(db, q, review_filter, page, size)


@admin_router.get("/{concept_id}", response_model=AdminConceptResponse)
def get_concept(
    concept_id: int,
    lang: Language = Query(default=Language.JA),
    db: Session = Depends(get_db),
    _: JWTPayload = Depends(require_admin),
):
    return _detail(db, concept_id, lang)


@admin_router.patch("/{concept_id}", response_model=AdminConceptResponse)
def update_gloss(
    concept_id: int,
    data: ConceptGlossUpdate,
    lang: Language = Query(default=Language.JA),
    db: Session = Depends(get_db),
    _: JWTPayload = Depends(require_admin),
):
    with _http_errors():
        concept_sense_service.update_gloss(
            db, concept_id, {f: getattr(data, f) for f in data.model_fields_set}
        )
    return _detail(db, concept_id, lang)


@admin_router.post(
    "/{concept_id}/terms", response_model=AdminConceptResponse, status_code=201
)
def add_term(
    concept_id: int,
    data: ConceptTermCreate,
    lang: Language = Query(default=Language.JA),
    db: Session = Depends(get_db),
    _: JWTPayload = Depends(require_admin),
):
    with _http_errors():
        concept_sense_service.add_teacher_term(
            db, concept_id, data.language, data.term, data.is_preferred
        )
    return _detail(db, concept_id, lang)


@admin_router.patch("/terms/{term_id}", response_model=AdminConceptResponse)
def update_term(
    term_id: int,
    data: ConceptTermUpdate,
    lang: Language = Query(default=Language.JA),
    db: Session = Depends(get_db),
    _: JWTPayload = Depends(require_admin),
):
    with _http_errors():
        concept_id = concept_sense_service.edit_term_by_id(
            db, term_id, data.term, data.is_preferred
        )
    return _detail(db, concept_id, lang)


@admin_router.delete("/terms/{term_id}", status_code=204)
def delete_term(
    term_id: int,
    db: Session = Depends(get_db),
    _: JWTPayload = Depends(require_admin),
):
    with _http_errors():
        concept_sense_service.delete_term_by_id(db, term_id)
    return Response(status_code=204)


@admin_router.post("/{concept_id}/merge", response_model=AdminConceptResponse)
def merge_concepts(
    concept_id: int,
    data: ConceptMergeRequest,
    lang: Language = Query(default=Language.JA),
    db: Session = Depends(get_db),
    _: JWTPayload = Depends(require_admin),
):
    if data.into_id == concept_id:
        raise HTTPException(
            status_code=422, detail="Cannot merge a concept into itself"
        )
    with _http_errors():
        concept_sense_service.merge_by_id(db, concept_id, data.into_id)
    return _detail(db, data.into_id, lang)


@admin_router.post(
    "/{concept_id}/split", response_model=AdminConceptResponse, status_code=201
)
def split_concept(
    concept_id: int,
    data: ConceptSplitRequest,
    lang: Language = Query(default=Language.JA),
    db: Session = Depends(get_db),
    _: JWTPayload = Depends(require_admin),
):
    with _http_errors():
        new_id = concept_sense_service.split_by_id(
            db,
            concept_id,
            data.question_ids,
            [NewTerm(language=t.language, term=t.term) for t in data.terms],
            gloss_ja=data.gloss_ja,
            gloss_en=data.gloss_en,
        )
    return _detail(db, new_id, lang)
