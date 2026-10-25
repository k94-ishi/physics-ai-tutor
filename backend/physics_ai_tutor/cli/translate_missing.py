import argparse
import sys

from physics_ai_tutor.database.database import SessionLocal
from physics_ai_tutor.repositories import question_repository
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.services.question_service import translate_missing_languages


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


def main(language: str | None, limit: int | None, dry_run: bool) -> int:
    db = SessionLocal()
    failures = 0

    try:
        languages = [Language(language)] if language else list(Language)
        seen: set[int] = set()

        for lang in languages:
            for question in question_repository.get_missing_language(db, lang, limit):
                if question.id in seen:
                    continue
                seen.add(question.id)

                if dry_run:
                    print(f"would translate: id={question.id} missing={lang}")
                    continue

                filled = translate_missing_languages(db, question.id)
                if filled:
                    print(f"translated: id={question.id} -> {','.join(filled)}")
                else:
                    failures += 1
                    print(f"failed: id={question.id}", file=sys.stderr)
    finally:
        db.close()

    return 1 if failures else 0


if __name__ == "__main__":
    args = parse_args()
    sys.exit(main(args.language, args.limit, args.dry_run))
