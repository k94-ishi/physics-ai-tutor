---
title: "[87] Asynchronize admin stats, exports and AI review runs; one ai_review_service"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], slice 6 of [73]

## Summary

Convert `api/v1/admin.py` - the usage dashboard, the review-agreement
report, the review export, and the AI review run endpoints - with the
stats, metrics and export services and the run side of
`ai_review_service`. The twin pairs in `ai_review_service` (29 sync, 10
async today) collapse to one implementation each.

## Motivation

`ai_review_service` is the module with the most duplication left from
[70]/[72]: grading, context building and run bookkeeping each exist
twice, and the nightly CLI ([26]) still uses the sync copies. The admin
routes here are low traffic, but the export streams a growing dataset
and the agreement report runs several aggregate queries, both of which
should not hold a thread.

## Scope

- Routes in `api/v1/admin.py`: `GET /admin/stats`, `GET
  /admin/reviews/export`, `GET /admin/stats/review-agreement`, `POST
  /admin/ai-review/runs`, `GET /admin/ai-review/runs`, `GET
  /admin/ai-review/runs/{id}`, `GET /admin/ai-review/pending-count`.
- `stats_service` and `stats_repository` (four): outright.
- `review_export_service` (`iter_export_rows`, `to_jsonl`;
  `default_since` is pure): outright; the export route becomes an async
  generator streaming the same NDJSON. `cli/export_reviews.py` wraps
  with `asyncio.run`.
- `review_metrics_service.build_report` and
  `review_metrics_repository` (three): outright; `compute_agreement`
  stays pure. `cli/review_metrics.py` wraps with `asyncio.run`.
- `ai_review_service`: `start_run` (budget and overlap guard),
  `list_runs`, `get_run`, `count_pending`, `count_stale`,
  `remaining_daily_budget`, `_fail_timed_out_runs`, `_build_context`,
  `review_question`, `grade_answer`. Delete each sync function whose
  async twin exists; the `async_` names stay until [88].
  `async_execute_run` and the background runner are already async
  ([72]).
- `ai_review_repository` (13 sync, 1 async): outright.
- `cli/review_pending.py` wraps with `asyncio.run`; exit codes 0/1/2 and
  the off-peak refusal unchanged, so the nightly workflow ([26]) does
  not change. `cli/eval_prompts.py` loses its sync `grade_answer` and
  `generate_answer` callers here too (`asyncio.run`; it needs no
  database).

## Acceptance criteria

- [ ] The seven routes are `async def` on `get_async_db`.
- [ ] Run semantics unchanged: 409 while a run is running, 429 when the
      24-hour budget is spent, a run silent for 30 minutes is marked
      failed by the next start ([34]); `pending`/`stale` counts and
      `would_review_*` identical.
- [ ] The export's line schema is byte-identical to today's for the
      same rows (pin with a fixture file).
- [ ] `ai_review_service` has no sync/async twin pairs;
      `test_ai_review_service.py` (33 tests) green on `async_db`.
- [ ] `review_pending`, `review_metrics`, `export_reviews` and
      `eval_prompts --dry-run` behave as before (`test_cli.py`,
      `test_eval_prompts.py`).

## Out of scope

- Any change to the agreement metrics, the export fields or the run
  budget.
- Deleting the sync engine and the `async_` prefixes ([88]).

## Technical notes

Reference on `wip/73-async-remaining`:
`git diff 260d7c2 9c42cfd -- backend/physics_ai_tutor/services/{ai_review,stats,review_export,review_metrics}_service.py backend/physics_ai_tutor/repositories/{ai_review,stats,review_metrics}_repository.py backend/physics_ai_tutor/api/v1/admin.py backend/physics_ai_tutor/cli/{review_pending,review_metrics,export_reviews,eval_prompts}.py`.
Every file here had no caller outside this slice except
`ai_review_service`, whose grading twin is also called from the ask
flow's post-generation task (already async) - so the WIP versions are
close to the target.

Test churn estimate: about 70 tests, the second-largest slice -
`test_ai_review_service.py` 33 (97 `db` references),
`test_review_metrics.py` 13, `test_review_export.py` 10,
`test_admin_stats.py` 6, `test_ai_review_schema.py` 5, parts of
`test_ai_review_queue.py`, `test_eval_prompts.py` and `test_cli.py`.
`test_background_concurrency.py` is already async and must stay green
as the run loop is touched.

Streaming the export: FastAPI's `StreamingResponse` accepts an async
generator; make sure the session is closed when the client disconnects
mid-stream (the dependency's `finally` handles it, but test it).

## Dependencies

- Blocked by: [83] (question read twins used by the run's context
  build). Independent of [84]-[86]; can run in parallel with them.
- Blocks: [88].

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Frontend untouched; CI green
- [ ] `.github/workflows/ai-review-nightly.yml` unchanged and the
      command verified locally with `--dry-run`
