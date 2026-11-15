---
title: "[103] Asynchronize the AI review run reads: list, detail, pending count"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [97] and [73]

## Summary

First slice of [97]: the read-only AI review run routes. No behaviour change.

## Scope

- Routes `GET /admin/ai-review/runs`, `GET /admin/ai-review/runs/{id}`,
  `GET /admin/ai-review/pending-count`.
- `ai_review_service.list_runs` and `get_run` outright (only these routes
  call them).
- `remaining_daily_budget`, `count_pending`, `count_stale` gain `async_`
  twins: the sync `start_run` and `cli/review_pending.py` still need the
  sync ones until [104]/[105].
- `ai_review_repository`: the pending and stale queries become
  session-free `select()` builders shared by both twins, so the rules
  cannot drift; async twins of the three counts.
- Delete the sync `execute_run_in_background`: nothing calls it since
  [72].

## Acceptance criteria

- [x] Same JSON from the three routes; `test_run_endpoints` and the
      pending-count tests green.
- [x] `stale` and `used_24h` are checked through the endpoint (no test
      looked at them before).

## Dependencies

- Blocked by: [96]
- Blocks: [104]

## Log

### 2026-11-15 — done

**Converted:** the three routes above; `list_runs` and `get_run`
outright. `async_remaining_daily_budget`, `async_count_pending`,
`async_count_stale` added beside the sync versions, which `start_run`
and the nightly CLI still call.

**Shared rules:** `_pending_question_query(db)` and
`_stale_question_query(db, ...)` (legacy `Query` objects tied to a sync
session) became `_pending_question_select()` and
`_stale_question_select(version)`, plain statements both twins run.
`_count_of()` wraps a statement in `SELECT count(*)`, which is what
`Query.count()` did. The sync list/count functions now use these too, so
their SQL meaning is unchanged and they cannot drift from the async ones.

**Deleted:** sync `execute_run_in_background`, which had no caller since
[72] moved the route to the async runner.

**New test:** `test_pending_count_reports_stale_and_used_budget`. Until
now every endpoint test had zero stale verdicts and zero used budget, so
the async stale query and the async 24 h count would have gone
untested. It also pins that an unparsed verdict stays pending while a
parsed one does not.

**Results:** 615 passed (614 + 1 new), `ruff check`, `ruff format
--check`, `mypy` clean. Frontend untouched.

## Rules (all [73] slices)

- Twins only while an unconverted caller needs the sync version; delete a
  sync function in the slice that removes its last caller.
- Tests that call converted code are async on `async_db`; arrange with
  `db` and commit. Frontend untouched.
- Reference production code: `git diff 260d7c2 9c42cfd -- <paths>` on
  `wip/73-async-remaining` (its twins are collapsed; adapt, do not copy).

## Definition of done

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] Log entry in this file; `status.md`, [67], [73] and [97] updated
