---
title: "[107] Delete the sync rate limiter and the dead sync repository functions"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [88] and [73]

## Summary

First slice of [88]: code nothing in the app calls. No behaviour change.

## Scope

- `rate_limit_service.check` / `record` and `rate_limit_repository`
  `count_recent_hits` / `record_hit` / `delete_hits_older_than`: the
  routes use the `async_` versions since [70]; only `test_rate_limit.py`
  calls the sync ones.
- Dead (no caller at all): `concept_term_repository.senses_by_words` and
  `get_many` (its only caller), `question_concept_repository.context_question`
  and `link_many`, `question_repository.set_text`.
- The five `test_rate_limit.py` unit tests move to the async functions,
  which until now were covered only through HTTP 429 tests.

## Acceptance criteria

- [x] The rate limiter has one implementation; its unit tests exercise it.

## Dependencies

- Blocked by: [97]
- Blocks: [110]

## Log

### 2026-11-16 — done

**Deleted from the app:** the sync `rate_limit_service.check` / `record`
and `rate_limit_repository.count_recent_hits` / `record_hit` /
`delete_hits_older_than`; the dead `concept_term_repository.senses_by_words`
and `get_many`, `question_concept_repository.context_question` and
`link_many`, and the repository-level `question_repository.set_text`
(the `Question.set_text` model method that services call is a different
function and stays). Each was re-checked with a plain text search before
deletion. Ruff dropped the imports this left unused. Surviving async
functions whose docstrings said "As `<deleted>`" now carry the deleted
originals' wording.

**Tests:** the five `test_rate_limit.py` unit tests now exercise the async
limiter the routes actually use; rows are arranged on `async_db` with
`flush()`, keeping each test inside one session as before. Same five
tests, same assertions.

**Results:** 622 passed, `ruff check`, `ruff format --check`, `mypy`
clean. Frontend untouched.

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
