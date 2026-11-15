---
title: "[105] Nightly review_pending CLI on the async executor; delete the sync run code"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [97] and [73]

## Summary

Third slice of [97]: the nightly CLI ([26]) uses the same async run
code as the admin button, and the sync run code is deleted.

## Scope

- `cli/review_pending.py` via `asyncio.run` on `async_start_run`,
  `async_execute_run` and the async counters. Arguments, messages and
  exit codes unchanged; `.github/workflows/ai-review-nightly.yml`
  unchanged.
- Delete the sync `start_run`, `_fail_timed_out_runs`,
  `eligible_question_ids`, `execute_run`, `_finish`,
  `remaining_daily_budget`, `count_pending`, `count_stale`, and the
  sync repository functions only they used.
- Tests: the six CLI tests (`_bind_review_cli` binds
  `AsyncSessionLocal`) and the executor tests that call the sync
  `execute_run` (counts and tokens, one failure, reviewed mid-run,
  unparsed retry, reaped executor stops).

## Behaviour the owner should confirm

The CLI today runs the **sync** executor, one question at a time. The
async executor is the one admin-started runs have used since [72]. Two
differences follow:

- The nightly run grades `AI_REVIEW_CONCURRENCY` questions at a time
  (what [72] measured: a 200-question run from over an hour to about
  twenty minutes).
- A question whose review raises counts as one failed item and the run
  goes on; the sync executor failed the whole run. A run that ends in
  any status other than `done` still exits 1.

## Acceptance criteria

- [ ] `test_ai_review_service.py` CLI and executor tests green on the
      async path; off-peak refusal (exit 2) and `--force` unchanged.
- [ ] No sync run function left in `ai_review_service`.

## Dependencies

- Blocked by: [104]
- Blocks: [106]

## Rules (all [73] slices)

- Twins only while an unconverted caller needs the sync version; delete a
  sync function in the slice that removes its last caller.
- Tests that call converted code are async on `async_db`; arrange with
  `db` and commit. A test that drives the CLI stays sync (`asyncio.run`
  cannot nest).
- Reference production code: `git diff 260d7c2 9c42cfd -- <paths>` on
  `wip/73-async-remaining` (its twins are collapsed; adapt, do not copy).

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Log entry in this file; `status.md`, [67], [73] and [97] updated
