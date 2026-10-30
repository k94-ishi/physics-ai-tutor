"""Print the prompt library as the model will see it, one record at a time."""

import argparse

from physics_ai_tutor.core.prompt_library import load_library


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", default=None, help="Show one family only.")
    return parser.parse_args()


def main(family: str | None = None) -> None:
    library = load_library()

    for record in library.records:
        if family is not None and record.family != family:
            continue

        language = record.language.value if record.language else "both"
        print(
            f"=== {record.family} / {record.name} ({language}) [{record.version}] ==="
        )
        if record.description:
            print(f"# {record.description}")
        print(record.text)
        print()


if __name__ == "__main__":
    args = parse_args()
    main(args.family)
