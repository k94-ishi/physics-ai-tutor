---
title: "[111] Test-only sync helpers in question_repository move out of the app"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [88] and [73]

## Summary

Fifth slice of [88]: `question_repository` sync functions that only
tests call. No behaviour change.

## Scope

- `create_question`, `create_questions`, `get_by_exact_text`,
  `get_question`, `update`, `update_content_and_status`, `update_status`.
- Tests that *test the repository* move to the async functions (as
  [107] did for the rate limiter); tests that only *arrange rows* use a
  sync helper in `tests/` (as [106]'s `create_ai_review`).
- ~30 tests, mostly `test_question_repository.py` and
  `test_question_service.py`; split again if it proves bigger.

## Acceptance criteria

- [ ] No sync function left in `question_repository`.

## Dependencies

- Blocked by: [110]
- Blocks: [98] (the rename would collide with the sync names)

## Rules (all [73] slices)

- Twins only while an unconverted caller needs the sync version; delete a
  sync function in the slice that removes its last caller.
- Tests that call converted code are async on `async_db`; arrange with
  `db` and commit. List `async_db` before `admin_client` ([87]).
- Reference production code: `git diff 260d7c2 9c42cfd -- <paths>` on
  `wip/73-async-remaining` (its twins are collapsed; adapt, do not copy).

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Log entry in this file; `status.md`, [67], [73] and [88] updated
