---
title: "[110] Delete the sync engine, SessionLocal, get_db, background_session and transaction() from the app"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [88] and [73]

## Summary

Fourth slice of [88] and its original core: one engine and one pool at
runtime. No behaviour change.

## Scope

- `database/database.py`: sync `engine` and `SessionLocal`;
  `database/dependency.py`: `get_db`; `database/session.py`:
  `background_session`; `database/transaction.py`: `transaction`.
- `tests/conftest.py` keeps its own sync engine for arranging rows (it
  already builds one); it stops overriding `get_db` and patching
  `session_module.SessionLocal`.
- `test_async_foundation.py` pool checks: only the async pool remains.

## Acceptance criteria

- [ ] `rg "SessionLocal|get_db"` matches only `database/`, `alembic/`,
      `tests/` (and `database/` only for the async names).
- [ ] One engine, one pool at runtime.

## Dependencies

- Blocked by: [107], [108], [109]
- Blocks: [99] (pool numbers), [74] (pool settings)

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
