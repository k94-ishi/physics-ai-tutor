---
title: "[104] Asynchronize starting an AI review run (POST /admin/ai-review/runs)"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [97] and [73]

## Summary

Second slice of [97]: the route that starts a run. No behaviour change.

## Scope

- Route `POST /admin/ai-review/runs` (still schedules
  `async_execute_run_in_background`).
- `async_start_run`, `_async_fail_timed_out_runs`,
  `async_eligible_question_ids` beside the sync versions, which
  `cli/review_pending.py` keeps until [105].
- `ai_review_repository`: async twins of `list_pending_question_ids`,
  `list_stale_question_ids`, `filter_reviewable_ids` on the statements
  [103] made shareable.
- Tests that only *start* runs move to `async_start_run` on `async_db`
  (check each; expected: second run refused, stale scope, selected
  scope, daily cap, timed-out run reaped, healthy run not reaped, the
  409 endpoint test).

## Acceptance criteria

- [x] 409 (run in progress, including a lost race on the unique index),
      429 (daily cap) and timeout reaping behave exactly as before.
- [x] Refusing to start still undoes the reaping (one transaction).
- [x] An `IntegrityError` that is not the single-running index is still
      re-raised, not reported as "in progress".

## Technical notes

Read scalars off the run row before the transaction can roll back
([70]); the refusal paths raise inside the transaction on purpose.

## Dependencies

- Blocked by: [103]
- Blocks: [105]

## Log

### 2026-11-16 — done

**Converted:** `POST /admin/ai-review/runs` is async and calls
`async_start_run`. **No route uses the sync `get_db` any more**;
`api/v1/admin.py` no longer imports the sync `Session`.

**Twins:** `async_start_run`, `async_eligible_question_ids` beside the
sync versions, which `cli/review_pending.py` keeps until [105]. The rules
are shared, not copied: the reap `UPDATE` (`_reap_statement`), the
"is a run in progress" query (`_running_run_select`), the new run row
(`_new_run`), the scope check and bound. The sync `start_run` now uses
the same helpers, so both versions issue the same SQL. Repository twins
`async_list_pending_question_ids`, `async_list_stale_question_ids`,
`async_filter_reviewable_ids` reuse [103]'s statements; the reviewable
filter and its order-keeping step are shared too.

**Tests moved to the async version (7):** second run refused, stale
scope, selected scope, daily cap (it spends the budget with
`async_execute_run`), timed-out run reaped, healthy run not reaped,
409 endpoint. The four tests that also run the sync executor stay for
[105].

**New tests (4)** for criteria nothing checked before: the route's
**429**; **losing the start race** (a rival commits after our
pre-check, so only the unique index can stop us; the test asserts the
"concurrent start" error); **another database error** (a missing
`started_by` user) is re-raised, not turned into a 409; **refusing to
start undoes the reaping**.

**Trap met again ([70]):** in the healthy-run test, the refused start
rolls back the async session, which expires the first run object;
reading `busy.id` afterwards needs IO and raises `MissingGreenlet`. The
test now reads the id first. Production code reads `running.id` before
raising and the route only reads the run after a successful start.

**Results:** 619 passed (615 + 4 new), `ruff check`, `ruff format
--check`, `mypy` clean. One earlier full run took 6.5 minutes and ended
with 1 failure and 7 errors starting in `test_users.py`; the details
were not kept. Three later full runs (45-62 s) and five repeated runs of
`test_ai_review_service.py` plus `test_users.py` were all clean, with
the machine at load ~4.8 from other sessions. Recorded in case it
shows up again.

## Rules (all [73] slices)

- Twins only while an unconverted caller needs the sync version; delete a
  sync function in the slice that removes its last caller.
- Tests that call converted code are async on `async_db`; arrange with
  `db` and commit. List `async_db` before `admin_client` ([87]).
- Reference production code: `git diff 260d7c2 9c42cfd -- <paths>` on
  `wip/73-async-remaining` (its twins are collapsed; adapt, do not copy).

## Definition of done

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] Log entry in this file; `status.md`, [67], [73] and [97] updated
