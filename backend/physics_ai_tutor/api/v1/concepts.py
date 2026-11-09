import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from physics_ai_tutor.api.dependencies import get_current_user_optional, require_admin
from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.models import Concept
from physics_ai_tutor.repositories import concept_term_repository
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
from physics_ai_tutor.schemas.token import JWTPayload, UserRole
from physics_ai_tutor.services import concept_sense_service
from physics_ai_tutor.services.concept_sense_service import (
    DuplicateTermError,
    NewTerm,
    TermSource,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/concepts", tags=["concepts"])
admin_router = APIRouter(prefix="/admin/concepts", tags=["admin"])


@router.get("", response_model=list[ConceptSearchItem])
def search_concepts(
    q: str = Query(default="", max_length=100),
    lang: Language = Query(default=Language.JA),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: JWTPayload | None = Depends(get_current_user_optional),
):
    """Concept senses by any of their words, in either language ([55])."""
    is_admin = current_user is not None and current_user.role == UserRole.ADMIN
    return concept_sense_service.search(
        db, q, lang.value, public=not is_admin, limit=limit
    )


# --- admin editor -------------------------------------------------------------


def _concept_or_404(db: Session, concept_id: int) -> Concept:
    concept = db.get(Concept, concept_id)
    if concept is None:
        raise HTTPException(status_code=404, detail="Concept not found")
    return concept


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
    concept = _concept_or_404(db, concept_id)
    for field in data.model_fields_set:
        setattr(concept, field, getattr(data, field) or None)
    db.commit()
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
    concept = _concept_or_404(db, concept_id)
    added = concept_sense_service.add_term(
        db,
        concept,
        data.language,
        data.term,
        TermSource.TEACHER,
        preferred=data.is_preferred or None,
    )
    if added is None:
        raise HTTPException(status_code=409, detail="The concept already has this word")
    db.commit()
    return _detail(db, concept_id, lang)


@admin_router.patch("/terms/{term_id}", response_model=AdminConceptResponse)
def update_term(
    term_id: int,
    data: ConceptTermUpdate,
    lang: Language = Query(default=Language.JA),
    db: Session = Depends(get_db),
    _: JWTPayload = Depends(require_admin),
):
    term = concept_term_repository.get_term(db, term_id)
    if term is None:
        raise HTTPException(status_code=404, detail="Term not found")
    try:
        concept_sense_service.edit_term(db, term, data.term, data.is_preferred)
    except DuplicateTermError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="The concept already has this word"
        ) from exc
    db.commit()
    return _detail(db, term.concept_id, lang)


@admin_router.delete("/terms/{term_id}", status_code=204)
def delete_term(
    term_id: int,
    db: Session = Depends(get_db),
    _: JWTPayload = Depends(require_admin),
):
    term = concept_term_repository.get_term(db, term_id)
    if term is None:
        raise HTTPException(status_code=404, detail="Term not found")
    concept_sense_service.delete_term(db, term)
    db.commit()
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
    source = _concept_or_404(db, concept_id)
    target = _concept_or_404(db, data.into_id)
    concept_sense_service.merge(db, source, target)
    db.commit()
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
    concept = _concept_or_404(db, concept_id)
    new = concept_sense_service.split(
        db,
        concept,
        data.question_ids,
        [NewTerm(language=t.language, term=t.term) for t in data.terms],
        gloss_ja=data.gloss_ja,
        gloss_en=data.gloss_en,
    )
    db.commit()
    return _detail(db, new.id, lang)
