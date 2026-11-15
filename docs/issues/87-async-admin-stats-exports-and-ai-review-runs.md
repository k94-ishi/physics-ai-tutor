---
title: "[87] Asynchronize the usage dashboard and the agreement report"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: admin stats. No behaviour change.

## Scope

- Routes `GET /admin/stats`, `GET /admin/stats/review-agreement`.
- `stats_service` + `stats_repository`, `review_metrics_service.build_report`
  + `review_metrics_repository` (outright); `cli/review_metrics.py` via
  `asyncio.run`.

## Acceptance criteria

- [x] `test_admin_stats.py` and `test_review_metrics.py` green.

## Dependencies

- Blocked by: [83]
- Blocks: [96]

## Log

### 2026-11-15 — done

**Converted:** `GET /admin/stats` and `GET /admin/stats/review-agreement`
are async; `stats_service`, `stats_repository` and
`review_metrics_service.build_report` outright; `cli/review_metrics.py`
runs the async service through `asyncio.run` (same arguments, same
output). No behaviour change.

**One twin, not "outright":** `review_metrics_repository` could not be
converted whole. The still-sync `review_export_service` calls its
`ai_reviews_by_question`, so that function keeps its sync version and
gains `async_ai_reviews_by_question`. Both share one statement
(`_ai_reviews_select`) and one grouping step, so their order cannot
drift. `list_pairs` is async outright. [96] removes the last sync caller
and deletes the sync twin.

**Tests:** the four `test_review_metrics.py` tests that call
`list_pairs` / `build_report` directly are async on `async_db`. They are
the first async tests that also use `admin_client`. Fixture order
matters: `db` and `async_db` both empty the tables, so `async_db` must
come **before** `admin_client`, or it deletes the admin user that
`admin_client` just created and the review route fails with a foreign
key error. The export-file test stays sync because it drives sync CLIs;
it reads the database report through a small `asyncio.run` helper, like
`conftest.create_user`. `test_admin_stats.py` is HTTP-only and did not
change.

**Results:** 614 passed (about 30 s), `ruff check` and `ruff format
--check` clean, `mypy` clean (171 files). Frontend untouched.

**What is left sync in the app:** the review export ([96]) and the four
AI-review-run routes ([97]) in `api/v1/admin.py`; `get_db` is used
nowhere else.

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

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] Log entry in this file; `status.md`, [67] and [73] updated
