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

- [x] `test_ai_review_service.py` CLI and executor tests green on the
      async path; off-peak refusal (exit 2) and `--force` unchanged.
- [x] No sync run function left in `ai_review_service`.
- [x] A crash stops the nightly run by default; `--continue-on-crash`
      keeps going (owner, 2026-11-16).

## Dependencies

- Blocked by: [104]
- Blocks: [106]

## Log

### 2026-11-16 — owner's answers

- Grading several questions at once: **accepted**.
- A crashing question: **must be controllable, default "stop the whole
  run"** (today's nightly behaviour). The exit code in that case was left
  to the implementer to decide; see below.

### 2026-11-16 — done

**What "crash" means.** Checked before designing: ordinary reviewer
failures (DeepSeek error, unreadable verdict, failed save) are caught
inside the review in *both* executors and are one failed item; the run
goes on, before and after this slice. The switch only concerns
unexpected errors *outside* the review (a bug, a database error loading
the question), which the sync executor turned into a failed run.

**The switch.** `async_execute_run(..., stop_on_crash=False)`; the CLI
passes `stop_on_crash=True` unless `--continue-on-crash` is given. A CLI
flag rather than an environment variable: only the nightly command uses
it and the workflow already passes its flags. Admin-page runs keep
continuing, unchanged. In stop mode the first crash is counted as one
failed item, no new item starts, the items already in flight finish and
are saved (their DeepSeek calls are paid for), and the run ends
`failed` with `question N crashed; see server logs`.

**Exit code decision: 1, as today.** A stopped run ends `failed`, and
the CLI already exits 1 for any run that is not `done`; with `--scope
both` it also skips the stale run, exactly as the sync CLI did. That is
right for a crash: it means a bug or an infrastructure problem, which
would likely repeat on every question, so the run should stop spending
budget and the job should fail so GitHub e-mails the owner. Nothing is
lost: finished reviews are kept, and the next run picks up the remaining
pending questions by itself. A separate exit code for "crashed" was
considered and not added: the workflow alerts on any non-zero code, and
the stderr line and the run's `error` already say what happened. With
`--continue-on-crash` a crash ends in `done` and exit 0, so it alerts
nobody; that is why it is not the default.

**Converted and deleted.** `cli/review_pending.py` runs everything
through `asyncio.run` (`async_count_*`, `async_start_run`,
`async_execute_run`); messages and exit codes unchanged;
`.github/workflows/ai-review-nightly.yml` unchanged (it gets the default,
stop). Deleted: sync `start_run`, `_fail_timed_out_runs`,
`eligible_question_ids`, `execute_run`, `_finish`,
`remaining_daily_budget`, `count_pending`, `count_stale`, and from the
repository `list_pending_question_ids`, `count_pending_questions`,
`count_created_since`, `list_stale_question_ids`, `count_stale_questions`,
`filter_reviewable_ids`. The surviving async functions got standalone
docstrings instead of "As `<deleted>`".

**Tests.** Moved to async: counts and tokens, one failure (now run in
stop mode, to pin that a reviewer failure never stops a run), reviewed
mid-run, unparsed retry, reaped executor stops (the rival start uses its
own session). The CLI tests stay sync (they drive `asyncio.run`); their
fixture binds `AsyncSessionLocal`. New: the crash switch both ways
(parametrized) and the CLI exiting 1 on a crash and 0 with
`--continue-on-crash`.

**Results:** 622 passed (619 + 3 new), `ruff check`, `ruff format
--check`, `mypy` clean. Frontend untouched.

## Rules (all [73] slices)

- Twins only while an unconverted caller needs the sync version; delete a
  sync function in the slice that removes its last caller.
- Tests that call converted code are async on `async_db`; arrange with
  `db` and commit. A test that drives the CLI stays sync (`asyncio.run`
  cannot nest).
- Reference production code: `git diff 260d7c2 9c42cfd -- <paths>` on
  `wip/73-async-remaining` (its twins are collapsed; adapt, do not copy).

## Definition of done

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] Log entry in this file; `status.md`, [67], [73] and [97] updated
