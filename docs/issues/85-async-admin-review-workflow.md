---
title: "[85] Asynchronize the review routes: review, bulk review, history"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: teacher review actions. No behaviour change.

## Scope

- Routes `GET /questions/{id}/reviews`, `POST /questions/{id}/review`,
  `POST /questions/bulk-review`.
- `question_review_service` and `question_review_repository` (outright).
- Async twins of `refresh_machine_translations` / `embed_language` for
  edit-approve; approve uses the async extraction from [91].

## Acceptance criteria

- [ ] Review rows identical (action, reason, language, before/after); `test_review_workflow.py` and `test_review_reasons.py` green.

## Dependencies

- Blocked by: [91]
- Blocks: [92]

## Log

### 2026-11-13 — re-scoped smaller

Owner found [83] (22 files, 35 tests) too big. The earlier, wider version of this issue was split; see [73]'s table.

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
