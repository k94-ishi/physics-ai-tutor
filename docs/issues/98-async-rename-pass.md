---
title: "[98] Rename pass: drop the `async_` prefixes"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: one mechanical rename. No behaviour change.

## Scope

- `async_<name>` becomes `<name>`; `get_async_db` becomes `get_db`,
  `async_transaction` becomes `transaction`, etc. One commit on a green
  suite, nothing else in it.

## Acceptance criteria

- [ ] No `async_` function names left in the app; suite green.

## Dependencies

- Blocked by: [88] (done 2026-11-16; no sync name is left to collide with)
- Blocks: [99]

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
