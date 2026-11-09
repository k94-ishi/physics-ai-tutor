from sqlalchemy.orm import Session

from physics_ai_tutor.models import Concept, Question, QuestionConcept


def link(db: Session, question_id: int, concept_id: int) -> None:
    exists = (
        db.query(QuestionConcept)
        .filter(
            QuestionConcept.question_id == question_id,
            QuestionConcept.concept_id == concept_id,
        )
        .first()
    )

    if exists is not None:
        return

    db.add(QuestionConcept(question_id=question_id, concept_id=concept_id))
    db.flush()


def get_concepts_for_question(db: Session, question_id: int) -> list[Concept]:
    return (
        db.query(Concept)
        .join(QuestionConcept, QuestionConcept.concept_id == Concept.id)
        .filter(QuestionConcept.question_id == question_id)
        .all()
    )


def get_concepts_for_questions(
    db: Session,
    question_ids: list[int],
    language: str = "ja",
    strict_language: bool = False,
) -> dict[int, list[str]]:
    """Concept names per question in `language`.

    Falls back to the other language unless `strict_language` is set, in
    which case concepts without a name in `language` are skipped.
    """
    if not question_ids:
        return {}

    rows = (
        db.query(QuestionConcept.question_id, Concept)
        .join(Concept, Concept.id == QuestionConcept.concept_id)
        .filter(QuestionConcept.question_id.in_(question_ids))
        .all()
    )

    result: dict[int, list[str]] = {question_id: [] for question_id in question_ids}
    for question_id, concept in rows:
        name = (
            concept.name_in(language)
            if strict_language
            else concept.display_name(language)
        )
        if name is not None:
            result[question_id].append(name)

    return result


def get_concept_ids_for_question(db: Session, question_id: int) -> list[int]:
    rows = (
        db.query(QuestionConcept.concept_id)
        .filter(QuestionConcept.question_id == question_id)
        .all()
    )

    return [concept_id for (concept_id,) in rows]


def get_questions_sharing_concepts(
    db: Session,
    question_id: int,
    exclude_ids: list[int],
    limit: int,
) -> list[int]:
    concept_ids_subquery = (
        db.query(QuestionConcept.concept_id)
        .filter(QuestionConcept.question_id == question_id)
        .scalar_subquery()
    )

    query = (
        db.query(QuestionConcept.question_id)
        .filter(QuestionConcept.concept_id.in_(concept_ids_subquery))
        .filter(QuestionConcept.question_id != question_id)
        .distinct()
    )

    if exclude_ids:
        query = query.filter(QuestionConcept.question_id.notin_(exclude_ids))

    rows = query.limit(limit).all()

    return [related_id for (related_id,) in rows]


def delete_by_question_id(db: Session, question_id: int) -> None:
    (
        db.query(QuestionConcept)
        .filter(QuestionConcept.question_id == question_id)
        .delete()
    )
    db.flush()


def context_question(db: Session, concept_id: int, language: str) -> str | None:
    """A question text in `language` that uses the concept, for translation."""
    column = Question.question_ja if language == "ja" else Question.question_en
    row = (
        db.query(column)
        .join(QuestionConcept, QuestionConcept.question_id == Question.id)
        .filter(QuestionConcept.concept_id == concept_id, column.is_not(None))
        .order_by(Question.status != "APPROVED", Question.id)
        .first()
    )
    return row[0] if row else None
