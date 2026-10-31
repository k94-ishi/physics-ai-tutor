#!/usr/bin/env python3
"""Import markdown issue drafts into git-bug (local, no remote needed).

Drafts are `NN-*.md` files with a YAML-ish front matter (title, labels,
milestone, priority) followed by the body. Dry-run by default; pass --apply
to create bugs. Existing bugs with the same title are reused, so the script
is safe to re-run. Draft cross-references like `#07` are rewritten to the
created bug's short id in a second pass.

git-bug keeps its data under refs/bugs in the repository's common .git, so
every worktree of this repository shares one store. Never run `git bug wipe`
to "start over": it deletes every bug and identity for every worktree.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "docs" / "issues"
DRAFT_GLOB = "[0-9][0-9]-*.md"
REFERENCE = re.compile(r"#(\d{2})\b")


@dataclass
class Draft:
    number: str
    title: str
    labels: list[str]
    body: str


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if match is None:
        raise ValueError("missing front matter")

    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()

    return meta, match.group(2).lstrip("\n")


def parse_labels(value: str) -> list[str]:
    return [item.strip() for item in value.strip("[]").split(",") if item.strip()]


def load_drafts(directory: Path) -> list[Draft]:
    drafts = []
    for path in sorted(directory.glob(DRAFT_GLOB)):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        # Milestone and priority become labels; git-bug has neither natively.
        labels = parse_labels(meta.get("labels", ""))
        labels.append(meta["milestone"].split()[0])
        labels.append(meta["priority"])
        drafts.append(
            Draft(
                number=path.name[:2],
                title=meta["title"].strip('"'),
                labels=labels,
                body=body,
            )
        )
    return drafts


def git_bug(*args: str) -> str:
    result = subprocess.run(
        ["git", "bug", *args], check=True, text=True, capture_output=True
    )
    return result.stdout


def existing_bugs() -> dict[str, str]:
    """Map title -> short id for every bug already in git-bug."""
    raw = git_bug("bug", "-f", "json").strip()
    if not raw:
        return {}

    return {item["title"]: item["human_id"] for item in json.loads(raw)}


def write_temp(body: str) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
        handle.write(body)
        return handle.name


def create_bug(draft: Draft) -> str:
    # With -F, git-bug takes the first line as the title and ignores -t.
    output = git_bug(
        "bug",
        "new",
        "-F",
        write_temp(f"{draft.title}\n\n{draft.body}"),
        "--non-interactive",
    )
    short_id = output.split()[0]
    git_bug("bug", "label", "new", short_id, *draft.labels)
    return short_id


def first_comment_id(short_id: str) -> str:
    data = json.loads(git_bug("bug", "show", short_id, "-f", "json"))
    return data["comments"][0]["id"]


def rewrite_references(drafts: list[Draft], mapping: dict[str, str]) -> None:
    for draft in drafts:
        short_id = mapping.get(draft.number)
        if short_id is None:
            continue

        def replace(match: re.Match[str]) -> str:
            target = mapping.get(match.group(1))
            return f"#{target}" if target is not None else match.group(0)

        new_body = REFERENCE.sub(replace, draft.body)
        if new_body == draft.body:
            continue

        print(f"rewrite  {short_id} cross-references")
        git_bug(
            "bug",
            "comment",
            "edit",
            first_comment_id(short_id),
            "-F",
            write_temp(new_body),
            "--non-interactive",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", default=DEFAULT_DIR, type=Path)
    parser.add_argument("--apply", action="store_true", help="create the bugs")
    args = parser.parse_args()

    drafts = load_drafts(args.directory)
    existing = existing_bugs() if args.apply else {}
    mapping: dict[str, str] = {}

    for draft in drafts:
        if draft.title in existing:
            mapping[draft.number] = existing[draft.title]
            print(f"skip     [{draft.number}] exists as {existing[draft.title]}")
            continue

        print(f"issue    [{draft.number}] {draft.title}")
        print(f"         labels={','.join(draft.labels)}")
        if args.apply:
            mapping[draft.number] = create_bug(draft)

    if args.apply:
        rewrite_references(drafts, mapping)
        print(f"\nDone: {len(mapping)} bugs. Browse with `git bug termui`.")
    else:
        print("\nDry run. Re-run with --apply to create the bugs in git-bug.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
