from sqlalchemy.orm import Session

from physics_ai_tutor.models import Concept, QuestionConcept


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
        .subquery()
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
