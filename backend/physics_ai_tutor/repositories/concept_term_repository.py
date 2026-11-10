from sqlalchemy import func, tuple_
from sqlalchemy.orm import Session

from physics_ai_tutor.models import Concept, ConceptTerm, Question, QuestionConcept


def senses_with_term(db: Session, language: str, normalized: str) -> list[Concept]:
    """Every sense that has this word in this language."""
    return (
        db.query(Concept)
        .join(ConceptTerm, ConceptTerm.concept_id == Concept.id)
        .filter(ConceptTerm.language == language, ConceptTerm.normalized == normalized)
        .distinct()
        .all()
    )


def senses_with_any_term(db: Session, normalized: str) -> list[Concept]:
    """Senses having this word in either language."""
    return (
        db.query(Concept)
        .join(ConceptTerm, ConceptTerm.concept_id == Concept.id)
        .filter(ConceptTerm.normalized == normalized)
        .distinct()
        .all()
    )


def search_terms(db: Session, needle: str, limit: int) -> list[ConceptTerm]:
    """Terms containing the normalised needle, either language."""
    return (
        db.query(ConceptTerm)
        .filter(ConceptTerm.normalized.contains(needle, autoescape=True))
        .limit(limit)
        .all()
    )


def question_counts(
    db: Session, concept_ids: list[int], statuses: list[str] | None
) -> dict[int, int]:
    """Linked questions per sense, optionally limited to some statuses."""
    if not concept_ids:
        return {}
    query = db.query(QuestionConcept.concept_id, func.count()).filter(
        QuestionConcept.concept_id.in_(concept_ids)
    )
    if statuses is not None:
        query = query.join(Question, Question.id == QuestionConcept.question_id).filter(
            Question.status.in_(statuses)
        )
    rows = query.group_by(QuestionConcept.concept_id).all()
    return {concept_id: count for concept_id, count in rows}


def get_term(db: Session, term_id: int) -> ConceptTerm | None:
    return db.get(ConceptTerm, term_id)


def get_many(db: Session, concept_ids: list[int]) -> list[Concept]:
    if not concept_ids:
        return []
    return db.query(Concept).filter(Concept.id.in_(concept_ids)).all()


def most_linked(db: Session, statuses: list[str] | None, limit: int) -> list[int]:
    """Senses with the most linked questions."""
    query = db.query(QuestionConcept.concept_id, func.count().label("n"))
    if statuses is not None:
        query = query.join(Question, Question.id == QuestionConcept.question_id).filter(
            Question.status.in_(statuses)
        )
    rows = (
        query.group_by(QuestionConcept.concept_id)
        .order_by(func.count().desc(), QuestionConcept.concept_id)
        .limit(limit)
        .all()
    )
    return [concept_id for concept_id, _ in rows]


def _shared_words_subquery(db: Session):
    # (language, normalized) pairs used by more than one sense.
    return (
        db.query(ConceptTerm.language, ConceptTerm.normalized)
        .group_by(ConceptTerm.language, ConceptTerm.normalized)
        .having(func.count(func.distinct(ConceptTerm.concept_id)) > 1)
        .subquery()
    )


def admin_concept_ids(db: Session, needle: str, review_filter: str) -> list[int]:
    """Sense ids for the admin editor, newest first.

    review_filter: "all", "review" (machine words or a language without a
    word), or "shared" (a word also used by another sense).
    """
    query = db.query(Concept.id)
    if needle:
        query = query.filter(
            Concept.id.in_(
                db.query(ConceptTerm.concept_id).filter(
                    ConceptTerm.normalized.contains(needle, autoescape=True)
                )
            )
        )
    if review_filter == "review":
        machine = db.query(ConceptTerm.concept_id).filter(
            ConceptTerm.source == "MACHINE"
        )
        query = query.filter(
            Concept.id.in_(machine)
            | Concept.name_ja.is_(None)
            | Concept.name_en.is_(None)
        )
    elif review_filter == "shared":
        shared = _shared_words_subquery(db)
        query = query.filter(
            Concept.id.in_(
                db.query(ConceptTerm.concept_id).join(
                    shared,
                    (shared.c.language == ConceptTerm.language)
                    & (shared.c.normalized == ConceptTerm.normalized),
                )
            )
        )
    return [cid for (cid,) in query.order_by(Concept.id.desc()).all()]


def shared_word_partners(db: Session, concept_ids: list[int]) -> dict[int, list[int]]:
    """For each sense, the other senses that share one of its words."""
    if not concept_ids:
        return {}
    mine = (
        db.query(ConceptTerm.language, ConceptTerm.normalized, ConceptTerm.concept_id)
        .filter(ConceptTerm.concept_id.in_(concept_ids))
        .subquery()
    )
    rows = (
        db.query(mine.c.concept_id, ConceptTerm.concept_id)
        .join(
            ConceptTerm,
            (ConceptTerm.language == mine.c.language)
            & (ConceptTerm.normalized == mine.c.normalized)
            & (ConceptTerm.concept_id != mine.c.concept_id),
        )
        .distinct()
        .all()
    )
    result: dict[int, list[int]] = {}
    for own, other in rows:
        result.setdefault(own, []).append(other)
    return {key: sorted(value) for key, value in result.items()}


def linked_questions(db: Session, concept_id: int, language: str) -> list[Question]:
    questions = (
        db.query(Question)
        .join(QuestionConcept, QuestionConcept.question_id == Question.id)
        .filter(QuestionConcept.concept_id == concept_id)
        .order_by(Question.id)
        .all()
    )
    for question in questions:
        question.resolve(language)
    return questions


WordKey = tuple[str, str]


def senses_by_words(db: Session, keys: set[WordKey]) -> dict[WordKey, list[Concept]]:
    """For each (language, normalized) word, the senses that have it.

    Two queries for any number of words, instead of one lookup per word.
    """
    if not keys:
        return {}
    rows = (
        db.query(ConceptTerm.language, ConceptTerm.normalized, ConceptTerm.concept_id)
        .filter(tuple_(ConceptTerm.language, ConceptTerm.normalized).in_(list(keys)))
        .all()
    )
    concepts = {c.id: c for c in get_many(db, list({cid for _, _, cid in rows}))}
    index: dict[WordKey, list[Concept]] = {}
    for language, normalized, concept_id in rows:
        index.setdefault((language, normalized), []).append(concepts[concept_id])
    return index
