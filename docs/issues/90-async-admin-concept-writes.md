---
title: "[90] Asynchronize the admin tag editor writes: gloss, words, merge, split"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: admin tag edits. No behaviour change.

## Scope

- Routes `PATCH /admin/concepts/{id}`, `POST .../terms`,
  `PATCH|DELETE .../terms/{term_id}`, `POST .../merge`, `POST .../split`.
- The write functions of `concept_sense_service`.
- `concept_term_repository` becomes async only (no sync caller left).

## Acceptance criteria

- [ ] 409 on duplicate word, label takeover on delete, merge and split behave as before (4 tests).

## Dependencies

- Blocked by: [89]
- Blocks: [91]

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
