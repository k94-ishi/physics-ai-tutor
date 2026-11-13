---
title: "[93] Asynchronize create and update (prepare/apply)"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: admin create and edit. No behaviour change.

## Scope

- Routes `POST /questions`, `PUT /questions/{id}`.
- `create_question`, `update_question`: translate and embed with no
  session, then one short transaction; both leave the [82] allowlist.
- Keep the legacy `question=/answer=/language=` form; pin it with a test.

## Acceptance criteria

- [ ] Create/update tests green; both body shapes accepted; rollback-on-embedding-failure tests still pass.

## Dependencies

- Blocked by: [86]
- Blocks: [94]

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
