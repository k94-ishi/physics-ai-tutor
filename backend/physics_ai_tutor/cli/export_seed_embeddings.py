"""Write the embeddings of the APPROVED questions and their tags to
seed_embeddings.jsonl.gz, so seeding needs no OpenAI call ([55]).

Question vectors are keyed by the exact text they embed (question or
answer, per language). A tag's vector is keyed by its `"<ja> | <en>"`
pair, the text the seed asks for when it creates the tag. No API calls.
"""

import argparse
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.text import concept_pair_text
from physics_ai_tutor.database import seed_embeddings
from physics_ai_tutor.database.database import SessionLocal
from physics_ai_tutor.models import (
    Concept,
    Question,
    QuestionConcept,
    QuestionEmbedding,
)
from physics_ai_tutor.services.embedding_service import vector_key


def collect(db: Session, model: str) -> dict[str, list[float]]:
    vectors: dict[str, list[float]] = {}
    rows = (
        db.query(QuestionEmbedding, Question)
        .join(Question, Question.id == QuestionEmbedding.question_id)
        .filter(
            Question.status == "APPROVED",
            QuestionEmbedding.model == model,
            QuestionEmbedding.chunk_index.is_(None),
        )
        .all()
    )
    for embedding, question in rows:
        text = question.text(embedding.language)
        if text is None:
            continue
        embedded = text[0] if embedding.type == "question" else text[1]
        vectors[vector_key(model, embedded)] = list(embedding.embedding)

    concepts = (
        db.query(Concept)
        .filter(
            Concept.embedding_model == model,
            Concept.id.in_(
                db.query(QuestionConcept.concept_id)
                .join(Question, Question.id == QuestionConcept.question_id)
                .filter(Question.status == "APPROVED")
            ),
        )
        .all()
    )
    for concept in concepts:
        vectors[
            vector_key(model, concept_pair_text(concept.name_ja, concept.name_en))
        ] = list(concept.embedding)
    return vectors


def main(out: Path) -> int:
    db = SessionLocal()
    try:
        vectors = collect(db, settings.embedding_model)
    finally:
        db.close()
    seed_embeddings.write(out, settings.embedding_model, vectors)
    print(f"Wrote {len(vectors)} vectors to {out}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=seed_embeddings.EMBEDDINGS_FILE)
    sys.exit(main(parser.parse_args().out))
