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

- [x] No sync function left in `question_repository`.

## Dependencies

- Blocked by: [110]
- Blocks: [98] (the rename would collide with the sync names)

## Log

### 2026-11-16 — done (no further split needed: most sites were one-line swaps)

**The seven sync functions fell into three groups:**

- **Arrangement (`create_question`).** Moved to
  `tests/conftest.create_question`, same signature including the legacy
  single-language `question=/answer=` form, built on the repository's
  shared `_new_question`. Eight test files swapped
  `question_repository.create_question(` for the helper; that covered
  most of the ~30 touched tests.
- **Readers with async twins** (`get_question`, `get_by_exact_text`,
  `update_status`). Their tests in `test_question_repository.py` moved
  to `async_get_question` / `async_get_by_exact_text` (8 tests,
  unchanged assertions); the two `create_question` behaviour tests moved
  to `async_create_question`. The one `update_status` arrangement call
  became a plain attribute set.
- **Dead code** (`update`, `update_content_and_status`,
  `create_questions`): no async twin and no production caller - the
  write service sets text and status directly since [93]. Deleted with
  their seven tests, which tested nothing the app runs; the three
  arrangement uses of `update_content_and_status` became attribute sets.

`question_repository` now imports only `AsyncSession`; its stale
"As `<sync twin>`" docstrings were rewritten.

**Results:** 615 passed (622 - the 7 dead-code tests), `ruff check`,
`ruff format --check`, `mypy` clean. Frontend untouched.

## Rules (all [73] slices)

- Twins only while an unconverted caller needs the sync version; delete a
  sync function in the slice that removes its last caller.
- Tests that call converted code are async on `async_db`; arrange with
  `db` and commit. List `async_db` before `admin_client` ([87]).
- Reference production code: `git diff 260d7c2 9c42cfd -- <paths>` on
  `wip/73-async-remaining` (its twins are collapsed; adapt, do not copy).

## Definition of done

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] Log entry in this file; `status.md`, [67], [73] and [88] updated
