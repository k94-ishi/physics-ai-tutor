---
title: "[83] Asynchronize the public question reads: list, detail, exact match, related, prerequisites"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], slice 2 of [73]

## Summary

The five student-facing read routes on `/questions` still run on the
thread pool. Convert them, with the services and the repository reads
behind them, to the async stack. No change in what any caller sees.

## Motivation

These are the highest-traffic routes after `/ai/ask`, and the first of
the slices [73] was split into. They are cheap (milliseconds of
database work), so the gain per request is small; the point is that
every student request stops competing for the 40 threads, and that the
read side of `question_repository` gains the async functions the admin
slices ([85], [86]) will reuse.

## Scope

- Routes in `api/v1/questions.py`: `GET /questions`, `GET
  /questions/exact-match`, `GET /questions/{id}`, `GET
  /questions/{id}/related`, `GET /questions/{id}/prerequisites`. They
  take `Depends(get_async_db)`; `search` is already async ([70]) and
  `_queue_translations` already hands work to async background tasks
  ([72]).
- Services, converted whole: `question_read_service.fetch_questions`,
  `fetch_question` (its inline lazy translation uses the async
  prepare/apply pair from [82]), `fetch_question_by_exact_text`;
  `question_presentation_service` (all six functions);
  `recommendation_service` (five); `prerequisite_service` (eleven).
  `concept_sense_service.concept_ids_missing_name` gets an `async_`
  twin; the rest of that module is [84].
- Repositories: `async_` twins for the read functions of
  `question_repository` (list, count, get, by ids, exact text, related
  candidates), `question_concept_repository` (concepts and concept ids
  for a question, `context_question`, the shared `_names_by_question`),
  `concept_repository` (`ids_missing_name`, `get_many`),
  `ai_review_repository.latest_for_questions`, and whatever
  `embedding_repository` read the related path needs that is not
  already `async_`.
- The sync originals **stay** where an unconverted caller still uses
  them (admin writes, the review flow, the seed) - the [70] twin rule.
  Where a twin would duplicate a rule (the status filter, the
  strict-language naming), extract the rule and share it; a filter that
  drifts between two copies is a security bug.
- Lazy relationship loads (`Question.concepts`, review rows on admin
  list items) become `selectinload` or explicit queries; `AsyncSession`
  raises on implicit IO.
- **Guard for every later slice:** make pytest treat `RuntimeWarning`
  ("coroutine ... was never awaited") as an error
  (`filterwarnings` in `pyproject.toml`). [72] found two vacuous tests
  this way, and the [73] attempt lost hours to an un-awaited
  `db.commit()` that deadlocked the next request instead of failing.

## Acceptance criteria

- [ ] No route in `api/v1/questions.py` resolves `get_db`; all six are
      `async def`.
- [ ] The strict-language tests ([53], `test_language_strict.py`) and
      the admin-fallback tests pass unchanged; `PUBLIC_HIDDEN_STATUSES`
      is applied through one shared predicate, not a copy.
- [ ] An un-awaited coroutine anywhere in the suite fails the run.
- [ ] Measured with `scripts/latency_probe.py` before and after:
      `/questions?size=50` and `/questions/{id}` at concurrency 32 show
      no regression (a small gain is expected, not required).

## Out of scope

- Concepts routes ([84]), admin routes ([85]-[87]), deleting the sync
  half ([88]).
- The three-request wave on the question page ([77]) and the pgvector
  index ([74]).

## Technical notes

The production side of this slice exists, type-checked, on the branch
`wip/73-async-remaining` (9c42cfd, directly on top of slice 1):
`git diff 260d7c2 9c42cfd -- backend/physics_ai_tutor/services/{question_read,question_presentation,recommendation,prerequisite}_service.py`
is the reference. It **collapsed** the twins, so take the async bodies
from it but keep the sync originals this slice still needs. Write the
test changes fresh: roughly 50 service and repository tests move from
`db` to `async_db` (`test_question_repository.py`,
`test_recommendation_service.py`, `test_prerequisites.py`, the read
half of `test_question_service.py`); the 83 API tests in
`test_questions.py` should barely change.

Convert callees before callers; never bridge with `run_in_executor`.
Read what you need off an ORM row before any transaction that might
roll back ([70] lesson).

## Dependencies

- Blocked by: none - slice 1 (auth, users, sessions) merged 2026-11-12.
- Blocks: [88]; makes [85]/[86] smaller (they reuse the repository
  twins added here).

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Frontend untouched; CI green
- [ ] Before/after numbers in this issue's Log
- [ ] No doc change expected; the dual-stack notes go in [88]
