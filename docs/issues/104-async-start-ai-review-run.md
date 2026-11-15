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

- [ ] 409 (run in progress, including a lost race on the unique index),
      429 (daily cap) and timeout reaping behave exactly as before.
- [ ] Refusing to start still undoes the reaping (one transaction).
- [ ] An `IntegrityError` that is not the single-running index is still
      re-raised, not reported as "in progress".

## Technical notes

Read scalars off the run row before the transaction can roll back
([70]); the refusal paths raise inside the transaction on purpose.

## Dependencies

- Blocked by: [103]
- Blocks: [105]

## Rules (all [73] slices)

- Twins only while an unconverted caller needs the sync version; delete a
  sync function in the slice that removes its last caller.
- Tests that call converted code are async on `async_db`; arrange with
  `db` and commit. List `async_db` before `admin_client` ([87]).
- Reference production code: `git diff 260d7c2 9c42cfd -- <paths>` on
  `wip/73-async-remaining` (its twins are collapsed; adapt, do not copy).

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Log entry in this file; `status.md`, [67], [73] and [97] updated
