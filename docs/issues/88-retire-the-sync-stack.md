---
title: "[88] Delete the sync engine, sync LLM clients and remaining sync twins"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: deletions. No behaviour change.

## Scope

- Delete sync `engine`, `SessionLocal`, `get_db`, `transaction()`,
  `background_session()` from the app, the sync LLM clients, and the
  last sync twins. `export_seed`, `export_seed_embeddings`, `init_db`
  via `asyncio.run`. Tests keep a test-only sync session in conftest.

## Acceptance criteria

- [ ] `rg "SessionLocal|get_db"` matches only `database/`, `alembic/`, `tests/`.

## Dependencies

- Blocked by: [95], [97] (both done 2026-11-16; unblocked)
- Blocks: [98]

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
