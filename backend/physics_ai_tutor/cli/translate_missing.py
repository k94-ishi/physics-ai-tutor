import argparse
import asyncio
import sys

from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.database.database import AsyncSessionLocal
from physics_ai_tutor.database.transaction import async_transaction
from physics_ai_tutor.repositories import question_repository
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.services.question_translation_service import (
    async_translate_missing_languages,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Machine-translate questions that lack text in a language.",
    )
    parser.add_argument(
        "--language",
        choices=[lang.value for lang in Language],
        default=None,
        help="Only fill this language (default: every missing language).",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


async def _missing_ids(
    db: AsyncSession, languages: list[Language], limit: int | None
) -> list[tuple[int, Language]]:
    """(question id, first missing language), each question once, in order."""
    seen: set[int] = set()
    found: list[tuple[int, Language]] = []
    for lang in languages:
        for question in await question_repository.get_missing_language(db, lang, limit):
            if question.id not in seen:
                seen.add(question.id)
                found.append((question.id, lang))
    return found


async def _run(language: str | None, limit: int | None, dry_run: bool) -> int:
    """Async since [102]; each question reads, translates and writes on its own."""
    languages = [Language(language)] if language else list(Language)
    failures = 0
    async with AsyncSessionLocal() as db:
        # A short read, released before any LLM call ([82]).
        async with async_transaction(db, "translate_missing_scan"):
            missing = await _missing_ids(db, languages, limit)
        for question_id, lang in missing:
            if dry_run:
                print(f"would translate: id={question_id} missing={lang}")
                continue

            filled = await async_translate_missing_languages(db, question_id)
            if filled:
                print(f"translated: id={question_id} -> {','.join(filled)}")
            else:
                failures += 1
                print(f"failed: id={question_id}", file=sys.stderr)

    return 1 if failures else 0


def main(language: str | None, limit: int | None, dry_run: bool) -> int:
    return asyncio.run(_run(language, limit, dry_run))


if __name__ == "__main__":
    args = parse_args()
    sys.exit(main(args.language, args.limit, args.dry_run))
