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

- [x] `rg "SessionLocal|get_db"` matches only `database/`, `alembic/`,
      `tests/` (and `database/` only for the async names).
- [x] One engine, one pool at runtime.

## Dependencies

- Blocked by: [107], [108], [109]
- Blocks: [99] (pool numbers), [74] (pool settings)

## Log

### 2026-11-16 — done

**Deleted from the app:** the sync `engine` and `SessionLocal`
(`database/database.py`), `get_db` (`database/dependency.py`),
`background_session` (`database/session.py`) and `transaction`
(`database/transaction.py`). Each module now holds only its async half,
with docstrings that no longer describe two stacks. The app has **one
engine and one pool** (`POOL_SIZE` 5 + `MAX_OVERFLOW` 10 per worker,
half of the two-pool total [75] measured); [74] and [99] re-read the
connection budget against it.

**Acceptance check:** a whole-word search for `SessionLocal` and
`get_db` finds them only in two test files, as strings that assert they
are gone. (A plain substring search also hits `AsyncSessionLocal` in
the CLIs, which is the async factory.) Alembic never used the app's
engine.

**Tests:** `conftest.py` stops patching `session_module.SessionLocal` and
overriding `get_db`, and keeps its own sync engine for arranging rows;
`test_async_hot_path.py` drops its `get_db` override.
`test_async_foundation.py`'s "both engines point at the same database"
became `test_the_app_has_one_engine_and_it_is_async`, and the pool-size
test checks the one pool.

**Left for [99]:** `test_architecture.py` still has
`test_async_code_never_uses_the_sync_transaction_helper`, now obsolete
since the helper is gone; [99] owns that file's cleanup and the new
"no sync `Session` outside `database/`, `alembic/`, `tests/`" rule.
The four repositories with test-only sync helpers still import `Session`
until [111]/[112].

**Docs:** `docs/development.md`'s layering rule told contributors to wrap
writes in the deleted `with transaction(...)`; it now names `async with
async_transaction(...)`, as do the [82] rule and the test-layout table.
The two-stacks section is marked as history until [99] removes it.

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
