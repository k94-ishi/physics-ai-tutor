---
title: "[92] Asynchronize the fill-translations route (`POST /questions/translate`)"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: admin translation trigger. No behaviour change.

## Scope

- Route `POST /questions/translate` onto the existing
  `async_translate_missing_languages`.

## Acceptance criteria

- [x] Translate-endpoint tests in `test_language.py` green.

## Dependencies

- Blocked by: [85]
- Blocks: [86]

## Rules (all [73] slices)

- Twins only while an unconverted caller needs the sync version; delete a
  sync function in the slice that removes its last caller.
- Tests that call converted code are async on `async_db`; arrange with
  `db` and commit. Frontend untouched.
- Reference production code: `git diff 260d7c2 9c42cfd -- <paths>` on
  `wip/73-async-remaining` (its twins are collapsed; adapt, do not copy).

## Definition of done

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] Log entry in this file; `status.md`, [67] and [73] updated

## Log

### 2026-11-13 — done

606 tests pass (605 + 1 new); ruff and mypy clean; frontend untouched.
1 production file, 1 test file.

- `POST /questions/translate` is async and calls the existing
  `async_translate_missing_languages`, which already reads, translates
  with no transaction, and writes per language ([82]).
- The sync `translate_missing_languages` stays: the `translate_missing`
  CLI uses it until [95].
- New test: a failed translation through the route reports
  `success: false` and leaves the row untranslated.
- Test database: the `elm` session was using the name this session had
  picked (`physics_ai_tutor_test_elm_session`), so the suite's lock
  refused a run. Left alone; this session's database name now carries a
  random part.
