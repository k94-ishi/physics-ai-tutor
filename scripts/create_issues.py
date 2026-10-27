#!/usr/bin/env python3
"""Create GitHub labels, milestones, and issues from docs/issues/*.md.

Dry-run by default; pass --apply to call `gh`. Requires `gh auth login`.
Draft cross-references like `#07` are rewritten to real issue numbers.
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
ISSUES_DIR = ROOT / "docs" / "issues"

LABEL_COLORS = {
    "deploy": "d93f0b",
    "ops": "fbca04",
    "privacy": "5319e7",
    "security": "b60205",
    "bug": "d73a4a",
    "feature": "0e8a16",
    "backend": "1d76db",
    "frontend": "006b75",
    "cli": "c5def5",
    "review": "0052cc",
    "ai-review": "6f42c1",
    "prompt": "e99695",
    "data-quality": "bfd4f2",
    "observability": "fef2c0",
    "testing": "d4c5f9",
}

MILESTONES = [
    "M0 Deploy Google Sign-In",
    "M1 Student value",
    "M2 Review data foundation",
    "M3 AI-assisted review (advisory)",
    "M4 Partial automation and regression safety",
]


@dataclass
class Draft:
    number: str
    title: str
    labels: list[str]
    milestone: str
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


def load_drafts() -> list[Draft]:
    drafts = []
    for path in sorted(ISSUES_DIR.glob("*.md")):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        drafts.append(
            Draft(
                number=path.name[:2],
                title=meta["title"].strip('"'),
                labels=parse_labels(meta.get("labels", "")),
                milestone=meta["milestone"],
                body=body,
            )
        )
    return drafts


def gh(*args: str, capture: bool = False) -> str:
    result = subprocess.run(
        ["gh", *args], check=True, text=True, capture_output=capture
    )
    return result.stdout if capture else ""


def ensure_labels(labels: set[str], apply: bool) -> None:
    for label in sorted(labels):
        color = LABEL_COLORS.get(label, "ededed")
        print(f"label    {label} ({color})")
        if apply:
            gh("label", "create", label, "--color", color, "--force")


def ensure_milestones(apply: bool) -> None:
    existing: set[str] = set()
    if apply:
        raw = gh(
            "api",
            "repos/{owner}/{repo}/milestones?state=all&per_page=100",
            capture=True,
        )
        existing = {item["title"] for item in json.loads(raw)}

    for title in MILESTONES:
        status = "exists" if title in existing else "create"
        print(f"milestone {title} ({status})")
        if apply and title not in existing:
            gh(
                "api",
                "repos/{owner}/{repo}/milestones",
                "-f",
                f"title={title}",
            )


def existing_issue_numbers_by_title(apply: bool) -> dict[str, int]:
    if not apply:
        return {}

    raw = gh(
        "issue",
        "list",
        "--state",
        "all",
        "--limit",
        "500",
        "--json",
        "number,title",
        capture=True,
    )
    return {item["title"]: item["number"] for item in json.loads(raw)}


def create_issue(draft: Draft, apply: bool) -> int | None:
    print(f"issue    [{draft.number}] {draft.title}")
    print(f"         labels={','.join(draft.labels)} milestone={draft.milestone}")
    if not apply:
        return None

    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
        handle.write(draft.body)
        body_path = handle.name

    url = gh(
        "issue",
        "create",
        "--title",
        draft.title,
        "--body-file",
        body_path,
        "--milestone",
        draft.milestone,
        *sum((["--label", label] for label in draft.labels), []),
        capture=True,
    ).strip()
    return int(url.rsplit("/", 1)[-1])


def rewrite_references(drafts: list[Draft], mapping: dict[str, int]) -> None:
    pattern = re.compile(r"#(\d{2})\b")

    for draft in drafts:
        number = mapping.get(draft.number)
        if number is None:
            continue

        def replace(match: re.Match[str]) -> str:
            target = mapping.get(match.group(1))
            return f"#{target}" if target is not None else match.group(0)

        new_body = pattern.sub(replace, draft.body)
        if new_body == draft.body:
            continue

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(new_body)
            body_path = handle.name

        print(f"rewrite  #{number} cross-references")
        gh("issue", "edit", str(number), "--body-file", body_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="call gh")
    args = parser.parse_args()

    drafts = load_drafts()
    ensure_labels({label for draft in drafts for label in draft.labels}, args.apply)
    ensure_milestones(args.apply)

    existing = existing_issue_numbers_by_title(args.apply)
    mapping: dict[str, int] = {}

    for draft in drafts:
        if draft.title in existing:
            number = existing[draft.title]
            print(f"skip     [{draft.number}] already exists as #{number}")
            mapping[draft.number] = existing[draft.title]
            continue

        number = create_issue(draft, args.apply)
        if number is not None:
            mapping[draft.number] = number

    if args.apply:
        rewrite_references(drafts, mapping)
    else:
        print("\nDry run. Re-run with --apply after `gh auth login`.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
