---
title: "[96] Asynchronize the review dataset export"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: admin export. No behaviour change.

## Scope

- Route `GET /admin/reviews/export` (async generator, same NDJSON).
- `review_export_service` (outright); `cli/export_reviews.py` via
  `asyncio.run`.

## Acceptance criteria

- [ ] Export lines byte-identical for the same rows (fixture); `test_review_export.py` green.

## Dependencies

- Blocked by: [87]
- Blocks: [97]

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
