---
title: "[94] Asynchronize JSONL import"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: admin import. No behaviour change.

## Scope

- Route `POST /questions/import`, `import_questions_from_jsonl`.
- Preferably after [76] (batch embeddings), whose collect-then-batch
  shape removes the last [82] allowlist entry.

## Acceptance criteria

- [ ] Import stays all-or-nothing; per-line errors unchanged.

## Dependencies

- Blocked by: [93] (and preferably [76])
- Blocks: [95]

## Rules (all [73] slices)

- Twins only while an unconverted caller needs the sync version; delete a
  sync function in the slice that removes its last caller.
- Tests that call converted code are async on `async_db`; arrange with
  `db` and commit. Frontend untouched.
- Reference production code: `git diff 260d7c2 9c42cfd -- <paths>` on
  `wip/73-async-remaining` (its twins are collapsed; adapt, do not copy).

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Log entry in this file; `status.md`, [67] and [73] updated
