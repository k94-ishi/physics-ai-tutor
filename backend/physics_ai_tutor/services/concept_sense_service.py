"""Concept senses and their terms ([55]).

A concept row is one meaning; its words live in `concept_terms`, any number
per language, shared across senses when the word is ambiguous. The
`name_ja`/`name_en` columns mirror the preferred term so older read paths
keep working until they are removed.
"""

import logging
import math
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from physics_ai_tutor.core.text import normalize_key
from physics_ai_tutor.database.transaction import async_transaction
from physics_ai_tutor.models import Concept, ConceptTerm, Question
from physics_ai_tutor.repositories import concept_repository, concept_term_repository
from physics_ai_tutor.schemas.concept import (
    AdminConceptListResponse,
    AdminConceptResponse,
    ConceptQuestionRef,
    ConceptSearchItem,
    ConceptTermResponse,
)

logger = logging.getLogger(__name__)

LANGUAGES = ("ja", "en")


class TermSource:
    EXTRACTED = "EXTRACTED"
    MACHINE = "MACHINE"
    TEACHER = "TEACHER"


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def has_term(concept: Concept, language: str, term: str) -> bool:
    key = normalize_key(term)
    return any(t.normalized == key for t in concept.terms_in(language))


def preferred_term(concept: Concept, language: str) -> ConceptTerm | None:
    return next((t for t in concept.terms_in(language) if t.is_preferred), None)


def sync_mirror(concept: Concept) -> None:
    """Copy the preferred term of each language into name_ja/name_en."""
    for language in LANGUAGES:
        preferred = preferred_term(concept, language)
        setattr(concept, f"name_{language}", preferred.term if preferred else None)


def _build_term(
    concept: Concept,
    language: str,
    term: str,
    source: str,
    preferred: bool | None,
) -> ConceptTerm | None:
    """The term a caller would add, or None when the sense already has it.

    Shared by the sync and async variants so the preferred-word rule
    cannot drift between them.
    """
    term = term.strip()[:255]
    if not term or has_term(concept, language, term):
        return None

    make_preferred = (
        preferred_term(concept, language) is None if preferred is None else preferred
    )
    if make_preferred:
        _clear_preferred(concept, language)

    return ConceptTerm(
        concept_id=concept.id,
        language=language,
        term=term,
        normalized=normalize_key(term),
        is_preferred=make_preferred,
        source=source,
    )


def add_term(
    db: Session,
    concept: Concept,
    language: str,
    term: str,
    source: str,
    preferred: bool | None = None,
) -> ConceptTerm | None:
    """Add a word to a sense; no-op when the sense already has it.

    `preferred=None` makes it preferred only when the language has none yet.
    """
    new = _build_term(concept, language, term, source, preferred)
    if new is None:
        return None

    concept.terms.append(new)
    db.flush()
    sync_mirror(concept)
    return new


async def async_add_term(
    db: AsyncSession,
    concept: Concept,
    language: str,
    term: str,
    source: str,
    preferred: bool | None = None,
) -> ConceptTerm | None:
    """As `add_term`, on an AsyncSession ([72])."""
    new = _build_term(concept, language, term, source, preferred)
    if new is None:
        return None

    concept.terms.append(new)
    await db.flush()
    sync_mirror(concept)
    return new


def _clear_preferred(concept: Concept, language: str) -> None:
    for existing in concept.terms_in(language):
        existing.is_preferred = False


async def set_preferred(db: AsyncSession, term: ConceptTerm) -> None:
    concept = await db.get(Concept, term.concept_id)
    assert concept is not None
    _clear_preferred(concept, term.language)
    await db.flush()
    term.is_preferred = True
    await db.flush()
    sync_mirror(concept)


async def delete_term(db: AsyncSession, term: ConceptTerm) -> None:
    """Remove a word; the oldest remaining word of that language takes over."""
    concept = await db.get(Concept, term.concept_id)
    assert concept is not None
    was_preferred = term.is_preferred
    concept.terms.remove(term)
    await db.flush()
    if was_preferred:
        remaining = sorted(concept.terms_in(term.language), key=lambda t: t.id)
        if remaining:
            remaining[0].is_preferred = True
    sync_mirror(concept)
    await db.flush()


async def merge(db: AsyncSession, source: Concept, target: Concept) -> None:
    """Fold `source` into `target`: links and words move, source is deleted."""
    target_questions = set(
        await concept_term_repository.linked_question_ids(db, target.id)
    )
    for link in await concept_term_repository.links_of(db, source.id):
        if link.question_id in target_questions:
            await db.delete(link)
        else:
            link.concept_id = target.id
    await db.flush()
    for term in list(source.terms):
        await async_add_term(
            db, target, term.language, term.term, term.source, preferred=False
        )
    for language in LANGUAGES:
        if not target.gloss_in(language) and source.gloss_in(language):
            setattr(target, f"gloss_{language}", source.gloss_in(language))
    await db.delete(source)
    await db.flush()
    logger.info("Concepts merged: source=%d target=%d", source.id, target.id)


@dataclass
class NewTerm:
    language: str
    term: str


async def split(
    db: AsyncSession,
    concept: Concept,
    question_ids: list[int],
    terms: list[NewTerm],
    gloss_ja: str | None = None,
    gloss_en: str | None = None,
    source: str = TermSource.TEACHER,
) -> Concept:
    """Move some questions to a new sense named by `terms`.

    The new sense starts from the old embedding: no embedding call, and a
    later extraction refines it through matching.
    """
    new = Concept(
        embedding=list(concept.embedding),
        extraction_model=concept.extraction_model,
        embedding_model=concept.embedding_model,
        extraction_prompt_version=concept.extraction_prompt_version,
        gloss_ja=gloss_ja,
        gloss_en=gloss_en,
        # Present, so `has_term` never lazy-loads it on an AsyncSession.
        terms=[],
    )
    db.add(new)
    await db.flush()
    for item in terms:
        await async_add_term(db, new, item.language, item.term, source)
    await concept_term_repository.move_links(db, concept.id, new.id, question_ids)
    await db.flush()
    logger.info(
        "Concept split: source=%d new=%d questions=%d",
        concept.id,
        new.id,
        len(question_ids),
    )
    return new


def label(concept: Concept, language: str) -> tuple[str, bool]:
    """Preferred word in `language`, else the other one; flag = fallback used."""
    preferred = preferred_term(concept, language)
    if preferred is not None:
        return preferred.term, False
    other = "en" if language == "ja" else "ja"
    fallback = preferred_term(concept, other)
    return (fallback.term if fallback else ""), True


# --- search ([55] stage 3) ------------------------------------------------------

PUBLIC_STATUSES = ["APPROVED"]


def _rank(term: ConceptTerm, key: str) -> int:
    if term.normalized == key:
        return 0 if term.is_preferred else 1
    return 2 if term.normalized.startswith(key) else 3


async def search(
    db: AsyncSession, query: str, language: str, public: bool, limit: int = 20
) -> list[ConceptSearchItem]:
    """Senses whose words (either language) contain `query`, best match first.

    Students only get senses with APPROVED questions and a label in their
    language (the strict rule of [53]); admins get every sense.
    """
    statuses = PUBLIC_STATUSES if public else None
    key = normalize_key(query) if query else ""
    if key:
        terms = await concept_term_repository.search_terms(db, key, limit * 10)
        best: dict[int, tuple[int, ConceptTerm]] = {}
        for term in terms:
            rank = _rank(term, key)
            if term.concept_id not in best or rank < best[term.concept_id][0]:
                best[term.concept_id] = (rank, term)
        concept_ids = list(best)
    else:
        best = {}
        concept_ids = await concept_term_repository.most_linked(db, statuses, limit * 2)

    counts = await concept_term_repository.question_counts(db, concept_ids, statuses)
    items = []
    for concept in await concept_term_repository.async_get_many(db, concept_ids):
        count = counts.get(concept.id, 0)
        text, fallback = label(concept, language)
        if public and (count == 0 or fallback):
            continue
        matched = best.get(concept.id)
        items.append(
            (
                matched[0] if matched else 0,
                -count,
                ConceptSearchItem(
                    id=concept.id,
                    label=text,
                    gloss=concept.gloss_in(language),
                    matched_term=matched[1].term if matched else None,
                    question_count=count,
                ),
            )
        )
    items.sort(key=lambda item: (item[0], item[1], item[2].label))
    return [item for _, _, item in items[:limit]]


# --- admin editor ([55] stage 4) ------------------------------------------------


def _admin_item(
    concept: Concept, count: int, shares: list[int]
) -> AdminConceptResponse:
    return AdminConceptResponse(
        id=concept.id,
        gloss_ja=concept.gloss_ja,
        gloss_en=concept.gloss_en,
        terms=[
            ConceptTermResponse.model_validate(term)
            for term in sorted(
                concept.terms, key=lambda t: (t.language, not t.is_preferred, t.id)
            )
        ],
        question_count=count,
        shares_word_with=shares,
    )


async def list_for_admin(
    db: AsyncSession, query: str, review_filter: str, page: int, size: int
) -> AdminConceptListResponse:
    ids = await concept_term_repository.admin_concept_ids(
        db, normalize_key(query) if query else "", review_filter
    )
    total = len(ids)
    page_ids = ids[(page - 1) * size : page * size]
    counts = await concept_term_repository.question_counts(db, page_ids, None)
    shares = await concept_term_repository.shared_word_partners(db, page_ids)
    concepts = {
        c.id: c for c in await concept_term_repository.async_get_many(db, page_ids)
    }
    items = [
        _admin_item(concepts[cid], counts.get(cid, 0), shares.get(cid, []))
        for cid in page_ids
        if cid in concepts
    ]
    return AdminConceptListResponse(items=items, total=total, page=page, size=size)


async def detail_for_admin(
    db: AsyncSession, concept_id: int, language: str
) -> AdminConceptResponse | None:
    concept = await db.get(Concept, concept_id)
    if concept is None:
        return None
    counts = await concept_term_repository.question_counts(db, [concept_id], None)
    shares = await concept_term_repository.shared_word_partners(db, [concept_id])
    item = _admin_item(concept, counts.get(concept_id, 0), shares.get(concept_id, []))
    item.questions = _question_refs(
        await concept_term_repository.linked_questions(db, concept_id, language)
    )
    return item


def _question_refs(questions: list[Question]) -> list[ConceptQuestionRef]:
    return [
        ConceptQuestionRef(id=q.id, question=q.question, status=q.status)
        for q in questions
    ]


class DuplicateTermError(Exception):
    """The sense already has this word in this language."""


async def edit_term(
    db: AsyncSession, term: ConceptTerm, new_text: str | None, preferred: bool | None
) -> None:
    """A teacher edit; the word counts as reviewed afterwards."""
    concept = await db.get(Concept, term.concept_id)
    assert concept is not None
    if new_text is not None and normalize_key(new_text) != term.normalized:
        if has_term(concept, term.language, new_text):
            raise DuplicateTermError(new_text)
        term.term = new_text
        term.normalized = normalize_key(new_text)
    term.source = TermSource.TEACHER
    await db.flush()
    if preferred:
        await set_preferred(db, term)
    sync_mirror(concept)
    await db.flush()


# --- editor use cases: one transaction each, called by the router ([59]) -------


class ConceptNotFoundError(Exception):
    """No concept with this id."""


class TermNotFoundError(Exception):
    """No concept term with this id."""


async def _concept(db: AsyncSession, concept_id: int) -> Concept:
    concept = await db.get(Concept, concept_id)
    if concept is None:
        raise ConceptNotFoundError(concept_id)
    return concept


async def _term(db: AsyncSession, term_id: int) -> ConceptTerm:
    term = await concept_term_repository.get_term(db, term_id)
    if term is None:
        raise TermNotFoundError(term_id)
    return term


async def update_gloss(
    db: AsyncSession, concept_id: int, changes: dict[str, str | None]
) -> None:
    """Set the given gloss fields; an empty string clears one."""
    async with async_transaction(db, "update_concept_gloss"):
        concept = await _concept(db, concept_id)
        for field, value in changes.items():
            setattr(concept, field, value or None)


async def add_teacher_term(
    db: AsyncSession, concept_id: int, language: str, term: str, is_preferred: bool
) -> None:
    """A word typed by a teacher; DuplicateTermError if the sense has it."""
    async with async_transaction(db, "add_concept_term"):
        concept = await _concept(db, concept_id)
        added = await async_add_term(
            db,
            concept,
            language,
            term,
            TermSource.TEACHER,
            preferred=is_preferred or None,
        )
        if added is None:
            raise DuplicateTermError(term)


async def edit_term_by_id(
    db: AsyncSession, term_id: int, new_text: str | None, preferred: bool | None
) -> int:
    """Edit a word or make it the label; returns its concept id."""
    async with async_transaction(db, "edit_concept_term"):
        term = await _term(db, term_id)
        concept_id = term.concept_id
        await edit_term(db, term, new_text, preferred)
    return concept_id


async def delete_term_by_id(db: AsyncSession, term_id: int) -> None:
    async with async_transaction(db, "delete_concept_term"):
        await delete_term(db, await _term(db, term_id))


async def merge_by_id(db: AsyncSession, source_id: int, into_id: int) -> None:
    async with async_transaction(db, "merge_concepts"):
        source = await _concept(db, source_id)
        await merge(db, source, await _concept(db, into_id))


async def split_by_id(
    db: AsyncSession,
    concept_id: int,
    question_ids: list[int],
    terms: list[NewTerm],
    gloss_ja: str | None = None,
    gloss_en: str | None = None,
) -> int:
    """Move questions to a new sense; returns the new concept id."""
    async with async_transaction(db, "split_concept"):
        new = await split(
            db,
            await _concept(db, concept_id),
            question_ids,
            terms,
            gloss_ja=gloss_ja,
            gloss_en=gloss_en,
        )
        new_id = new.id
    return new_id


async def concept_ids_missing_name(
    db: AsyncSession, question_ids: list[int], language: str
) -> list[int]:
    """Concepts of these questions without a word in `language` ([53])."""
    return await concept_repository.ids_missing_name(db, question_ids, language)
