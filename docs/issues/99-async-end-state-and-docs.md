---
title: "[99] Async end state: architecture test, docs, connection budget"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: closing the migration. No behaviour change.

## Scope

- `test_architecture.py` forbids sync `Session` and `sessionmaker`
  outside `database/`, `alembic/`, `tests/`; obsolete checks removed
  (at least `test_async_code_never_uses_the_sync_transaction_helper`,
  whose helper [110] deleted).
- `docs/development.md`: drop the two-stack section; one pool per worker.
- Re-measure connections per worker ([75] table) on a quiet machine.

## Acceptance criteria

- [ ] [73]'s acceptance criteria all ticked; [73] closed.

## Dependencies

- Blocked by: [98] (done 2026-11-17)
- Blocks: closes [73]

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
