---
title: Export the human review dataset as JSONL
labels: [feature, review, ai-review, backend, cli]
milestone: M2 Review data foundation
priority: P2
---

**Priority:** P2  **Milestone:** M2 — Review data foundation

## Summary

A CLI (and admin-only endpoint) that writes one JSONL line per review:
question, AI answer, human verdict, reason, corrected answer, generation
metadata, and language.

## Motivation

Everything the AI-review work needs is in Postgres but scattered across
`questions`, `question_reviews`, `question_concepts`, and (after #09)
generation metadata. A stable export format lets prompts be evaluated
offline (#15, #17) without touching production, and gives a reproducible
dataset to show.

## Scope

- `physics_ai_tutor/cli/export_reviews.py --since DATE --out file.jsonl`.
- Line schema (document in `docs/database.md`):
  `question_id, language, source, generation_model, prompt_version,
  generation_mode, retrieved_question_ids, concepts, question, answer_before,
  answer_after, action, reason, comment, reviewer_kind, reviewed_at`.
- Exclude rows older than the #07 fix date by default (flag to include).
- Admin endpoint `GET /api/v1/admin/reviews/export` streaming the same
  format, for when the CLI has no DB access.
- No personal data: reviewer id is replaced by `reviewer_kind` and a stable
  hash.

## Acceptance criteria

- [ ] Export of the test database round-trips through `json.loads`.
- [ ] Rows from before the cutoff are excluded unless `--all`.

## Out of scope

- Any training; this is data plumbing.

## Technical notes

Reuse the `_bind_cli_sessions` pattern from `tests/test_cli.py`.

## Dependencies

- Blocked by: #08, #09
- Blocks: #15, #16, #17

## Definition of done

- [ ] Backend checks pass; CLI test with a small fixture
- [ ] `docs/development.md` lists the command
