"""Write the APPROVED questions of a database to seed.jsonl ([55], [101]).

Keeps what only the database knows and an LLM produced: both languages
with their provenance, the tags as `"<ja> | <en>"` pairs (preferred
words), and the difficulty levels. Existing seed entries keep their order
(matched by Japanese question text); new rows are appended by id. No API
calls. Aliases and glosses are not part of the seed format yet; the
command reports them so nothing is lost silently.
"""

import argparse
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from physics_ai_tutor.core.text import concept_line
from physics_ai_tutor.database import seed_file
from physics_ai_tutor.database.database import SessionLocal
from physics_ai_tutor.models import Concept, Question, QuestionConcept
from physics_ai_tutor.schemas.language import TextProvenance

SEED_FILE = seed_file.SEED_FILE


def _entry(question: Question, tags: list[str]) -> dict:
    entry: dict = {}
    for lang in ("ja", "en"):
        if getattr(question, f"question_{lang}") is None:
            continue
        entry[f"question_{lang}"] = getattr(question, f"question_{lang}")
        entry[f"answer_{lang}"] = getattr(question, f"answer_{lang}")
    # HUMAN is what the importer assumes for a supplied text; record others.
    for lang in ("ja", "en"):
        provenance = getattr(question, f"{lang}_provenance")
        if provenance == TextProvenance.MACHINE:
            entry[f"{lang}_provenance"] = provenance
    entry["physics_level"] = question.physics_level
    entry["math_level"] = question.math_level
    entry["tags"] = tags
    return entry


def build_entries(db: Session, order: list[str]) -> tuple[list[dict], list[str]]:
    """Seed entries in `order` (Japanese texts), plus notes on lost detail."""
    questions = (
        db.query(Question)
        .filter(Question.status == "APPROVED")
        .order_by(Question.id)
        .all()
    )
    links = (
        db.query(QuestionConcept.question_id, Concept)
        .join(Concept, Concept.id == QuestionConcept.concept_id)
        .filter(QuestionConcept.question_id.in_([q.id for q in questions]))
        .order_by(QuestionConcept.question_id, Concept.id)
        .all()
    )
    tags: dict[int, list[str]] = {}
    notes: set[str] = set()
    for question_id, concept in links:
        tags.setdefault(question_id, []).append(
            concept_line(concept.name_ja, concept.name_en)
        )
        if len(concept.terms) > len([t for t in concept.terms if t.is_preferred]):
            notes.add(f"concept {concept.id} has aliases (not exported)")
        if concept.gloss_ja or concept.gloss_en:
            notes.add(f"concept {concept.id} has a gloss (not exported)")

    rank = {text: index for index, text in enumerate(order)}
    questions.sort(key=lambda q: (rank.get(q.question_ja or "", len(rank)), q.id))
    entries = [_entry(q, tags.get(q.id, [])) for q in questions]
    return entries, sorted(notes)


def main(out: Path) -> int:
    order: list[str] = []
    if SEED_FILE.exists():
        order = [
            e.get("question_ja") or e.get("question") or ""
            for e in seed_file.read_entries(SEED_FILE)
        ]

    db = SessionLocal()
    try:
        entries, notes = build_entries(db, order)
    finally:
        db.close()

    seed_file.write_entries(entries, out)
    for note in notes:
        print(f"note: {note}", file=sys.stderr)
    print(f"Wrote {len(entries)} entries to {out}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=SEED_FILE)
    sys.exit(main(parser.parse_args().out))
