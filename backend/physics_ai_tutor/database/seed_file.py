"""Read and write seed.jsonl, the reviewable seed content ([101]).

One JSON object per line, in a fixed order: both languages, provenance
when machine-made, the two difficulty levels and the tags as
`"<ja> | <en>"` pairs. One question per line keeps a diff to the lines
that changed. The same lines are also valid input for the admin
"Upload" page, which reads the texts and ignores the other fields.
"""

import json
from pathlib import Path

SEED_FILE = Path(__file__).resolve().parent / "seed.jsonl"


def read_entries(path: Path = SEED_FILE) -> list[dict]:
    """Every entry in file order; blank lines are skipped."""
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_entries(entries: list[dict], path: Path = SEED_FILE) -> None:
    """One entry per line, non-ASCII kept readable, ending in a newline."""
    with open(path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
