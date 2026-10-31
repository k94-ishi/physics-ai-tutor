---
title: "[34] Bug: AI review run lifecycle: timed-out runs resurrect, skips count as failures, unparsed verdicts never retried"
labels: [bug, ai-review, backend]
milestone: M3 AI-assisted review (advisory)
priority: P1
---

**Priority:** P1  **Milestone:** M3 — AI-assisted review (advisory)

## What happened

Code review of the [25] `bec062c` orchestration
(`backend/physics_ai_tutor/services/ai_review_service.py`) found six
defects. The first one invalidates the overlap guard that [26] `e0594f1`
and [27] `0d50e7e` build on, so it should land before those.

1. **A timed-out run resurrects and overlaps the next one.** The guard
   marks a > 30-min run `failed` (`ai_review_service.py:336-347`) and lets
   a new run start, but the old executor never re-checks `run.status`
   inside its loop (`execute_run`, :397-429), so it keeps making DeepSeek
   calls concurrently, and at :418 unconditionally sets `status="done"`,
   overwriting `failed`. Not theoretical: `RUN_TIMEOUT_MINUTES = 30`
   (:296) while a full-cap run (200 questions at ~10 s per call) takes
   longer than 30 minutes, so a legitimate run trips it with no crash.
2. **Skipped questions are counted as failures.** `execute_run`
   (:408-409) increments `failed_count` whenever `review_question` returns
   None, but None also means "skipped: not AI-generated or already
   human-reviewed" (:226-234). A teacher reviewing a question between run
   start and execution produces spurious failures; [28] `c03d036` requires
   skips to be reported as skips.
3. **Parse-failure reviews are never retried.** A question whose only
   `ai_reviews` row has `verdict NULL` under the current prompt version is
   excluded from `pending` (it has a row —
   `repositories/ai_review_repository.py:66-84`) and from `stale` (version
   matches — :100-129); only a manual `scope=selected` run reaches it.
4. **`pending-count` is capped at the daily cap.** `api/v1/admin.py:189-190`
   routes through `eligible_question_ids`, which bounds at
   `ai_review_daily_cap` (`ai_review_service.py:320`); with 300 pending the
   preview says 200, and it ignores the *remaining* budget. [27]'s confirm
   dialog would show wrong numbers.
5. **`review_pending` exits 0 on a failed run.**
   `cli/review_pending.py:55-57` never calls `sys.exit` with a status;
   scheduled-run alerting ([26]) cannot detect failure.
6. **`start_run` reports any IntegrityError as 409 "run in progress"**
   (`ai_review_service.py:389-392`), e.g. an FK violation on `started_by`.

Minor, fix in passing: `deepseek_service.py:88` stores the configured model
alias instead of `response.model`; the ja rubric in `prompt_library.yaml`
has the typo 機会的 for 機械的 (fingerprint bump + eval re-run required, so
coordinate with [33]).

## What should have happened

One run at a time, honest counts (reviewed / failed / skipped), every
unreviewed question eventually reviewed, failures visible to schedulers.

## Scope

- Executor re-checks `run.status` each iteration and stops when it is no
  longer `running`; `done` is only written over `running`.
- Either raise the timeout above the worst-case full-cap duration or have
  the executor heartbeat (`updated_at`) so the guard only reaps truly dead
  runs.
- Add `skipped_count` to `ai_review_runs` (migration) or stop counting
  skips as failures and report them in the run payload.
- Treat a NULL-verdict row under the current prompt version as pending (or
  stale) so parse failures retry.
- `pending-count` returns the true counts plus the remaining daily budget.
- CLI exits non-zero when the run ends `failed`.
- Distinguish the unique-index violation from other IntegrityErrors.

## Acceptance criteria

- [ ] A run whose executor outlives the timeout cannot flip a `failed` run
      back to `done`, and two executors never run concurrently (test).
- [ ] A run over questions that were human-reviewed mid-run reports them
      skipped, not failed (test).
- [ ] A question with only an unparsed verdict reappears in the pending or
      stale scope (test).
- [ ] `review_pending` exits 1 on a failed run (test).

## Definition of done

- [ ] Regression tests added; backend checks pass
- [ ] `docs/api.md` updated where response shapes change
