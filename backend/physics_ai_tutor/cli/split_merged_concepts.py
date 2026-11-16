"""Split concept senses that the old name-matching rule glued together ([55]).

Before [55], a newly extracted `<ja> | <en>` pair joined any concept that
shared *one* of its words, and the differing word was dropped: 相 | phase
landed on 位相 | phase, 位相 | topology too. Such a link is recognisable
afterwards: the question's own text uses none of the sense's words in its
original language.

Detection is offline (--dry-run prints the report and stops). The split
itself re-extracts each suspect question under the new matching rules,
which puts its concepts on the right senses; one DeepSeek call per
question, off-peak window like backfill_levels unless --force.
"""

import argparse
import asyncio
import sys
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.cli.review_pending import (
    EXIT_FAILED,
    EXIT_OK,
    EXIT_OUTSIDE_WINDOW,
    _now,
    within_offpeak,
)
from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.text import normalize_key
from physics_ai_tutor.database.database import AsyncSessionLocal
from physics_ai_tutor.models import Concept, Question, QuestionConcept
from physics_ai_tutor.schemas.concept import ConceptExtractionResult
from physics_ai_tutor.services import question_write_service


@dataclass
class SuspectLink:
    question_id: int
    concept_id: int
    question: str
    concept_words: list[str]


def _uses_a_word(question: Question, concept: Concept) -> bool:
    language = question.original_language
    text = question.original_text()
    haystack = normalize_key(" ".join(text))
    return any(term.normalized in haystack for term in concept.terms_in(language))


async def find_suspect_links(db: AsyncSession) -> list[SuspectLink]:
    """Links whose question never uses the sense's words in its own language."""
    # `Concept.terms` loads eagerly (selectin), so the checks below need no IO.
    rows = (
        await db.execute(
            select(Question, Concept)
            .join(QuestionConcept, QuestionConcept.question_id == Question.id)
            .join(Concept, Concept.id == QuestionConcept.concept_id)
            .order_by(Question.id, Concept.id)
        )
    ).all()
    suspects = []
    for question, concept in rows:
        if not concept.terms_in(question.original_language):
            continue
        if _uses_a_word(question, concept):
            continue
        suspects.append(
            SuspectLink(
                question_id=question.id,
                concept_id=concept.id,
                question=question.original_text()[0],
                concept_words=[t.term for t in concept.terms],
            )
        )
    return suspects


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print the suspect links; no API calls, no changes.",
    )
    parser.add_argument(
        "--limit", type=int, default=50, help="Maximum questions this run."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even outside the off-peak window (full price).",
    )
    return parser.parse_args()


async def _reextract(question_ids: list[int]) -> list[ConceptExtractionResult]:
    """Re-extraction is async since [91]; the CLI drives it with its own session."""
    async with AsyncSessionLocal() as session:
        return await question_write_service.reextract_concepts_for_questions(
            session, question_ids
        )


async def _suspects() -> list[SuspectLink]:
    """A short read; its session closes before any DeepSeek call ([82])."""
    async with AsyncSessionLocal() as db:
        return await find_suspect_links(db)


def main(dry_run: bool = False, limit: int = 50, force: bool = False) -> int:
    return asyncio.run(_run(dry_run, limit, force))


async def _run(dry_run: bool, limit: int, force: bool) -> int:
    """Async since [109]; one event loop for the whole command."""
    suspects = await _suspects()
    question_ids = list(dict.fromkeys(s.question_id for s in suspects))
    for suspect in suspects:
        print(
            f"q{suspect.question_id} {suspect.question[:40]!r} -> "
            f"concept {suspect.concept_id} {suspect.concept_words}"
        )
    print(f"{len(suspects)} suspect links on {len(question_ids)} questions")

    if dry_run or not question_ids:
        return EXIT_OK
    if not force and not within_offpeak(
        _now(), settings.ai_review_offpeak_start, settings.ai_review_offpeak_end
    ):
        print(
            "Refusing to re-extract outside the DeepSeek off-peak window; "
            "use --force or --dry-run.",
            file=sys.stderr,
        )
        return EXIT_OUTSIDE_WINDOW

    results = await _reextract(question_ids[:limit])
    failed = sum(1 for result in results if not result.success)
    remaining = len(question_ids) - len(results)
    print(
        f"Re-extracted {len(results) - failed} questions ({failed} failed)"
        + (f"; {remaining} remain - re-run to continue" if remaining else "")
    )
    return EXIT_OK if failed == 0 else EXIT_FAILED


if __name__ == "__main__":
    args = parse_args()
    sys.exit(main(args.dry_run, args.limit, args.force))
