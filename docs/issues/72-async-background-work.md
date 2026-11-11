---
title: "[72] Background work on the event loop: parallel translations, bounded AI-review concurrency"
labels: [backend, async, performance]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67]

## Summary

Move all background work off the thread pool onto the event loop, and
let independent external calls run at the same time under small, named
concurrency limits: list translations a few questions at a time, and AI
review runs a few questions at a time. Wall-clock time for translation
backlogs and review runs drops roughly by the concurrency factor.

## Motivation

After [70] the request path is async, but background bodies converted as
callees still run one item at a time, and anything still sync occupies
threads. A 50-question review run is 50 sequential DeepSeek calls
(minutes); a page of untranslated rows is translated one row at a time.
These waits are independent of each other — serialising them is pure
queueing, and it delays what students see ([53] translations) and what
teachers find in the morning ([26] runs).

## Scope

- Every `BackgroundTasks.add_task` target is an async function
  (`ai.py`, `questions.py`, `admin.py`); no background body left on the
  thread pool.
- `background_translation_service`: `translate_missing` processes its
  claimed ids under an `asyncio.Semaphore` (start at 3). Same
  guarantees: approved-only re-check, one DeepSeek call per row at most,
  never raises. The `threading.Lock` in-flight sets become single-loop
  state here — which is enough for *one* process and no more; making the
  claim correct across processes is [75], and the two are independent
  (a semaphore bounds one worker's rate, a database claim bounds all
  workers' duplication). Do not treat this step as fixing that.
- `ai_review_service.execute_run`: review up to K questions at a time
  (setting `AI_REVIEW_CONCURRENCY`, default 3). Keep the per-item
  transaction so progress polling still sees counts grow; keep the
  heartbeat fresh; the fixed `question_ids` list, the daily budget and
  the single-running-run guard are decided at `start_run` time and are
  unaffected by in-run concurrency. Takeover/timeout semantics from [34]
  must survive: on `status != running` the remaining items stop.
- Each concurrent review item needs its own `AsyncSession` (sessions are
  not concurrency-safe); the run-row updates happen in one place.
- `translate_into` stays translation-then-embedding (the embedding needs
  the translated text), but a question's independent targets and the
  question/answer embedding pair may run concurrently if it stays simple.

## Acceptance criteria

- [ ] No `threading` primitives left in services (process-local claim
      state remains until [75] replaces it).
- [ ] A review run with delayed mock calls finishes ~K times faster than
      sequential, with correct counts, token totals and heartbeat.
- [ ] A run that is reaped mid-flight stops its remaining items ([34]
      semantics), covered by a test.
- [ ] Translation claims still prevent duplicate work under concurrency.
- [ ] Daily budget never exceeded, including at run start under
      concurrency (existing guard, re-tested).

## Out of scope

- A real job queue or worker process. `BackgroundTasks` in-process
  remains the model; revisit only if the single Render instance becomes
  the bottleneck.
- Making the de-duplication safe across processes ([75]), and therefore
  running more than one worker.
- The nightly workflow itself ([26]) — it calls the CLI, which wraps the
  async service with `asyncio.run` and behaves identically.

## Technical notes

Concurrency multiplies the DeepSeek request rate — keep defaults low and
configurable; the off-peak window logic and context-caching benefit (the
shared rubric prefix) are per-request and survive concurrency. In-process
background tasks die with a deploy/restart, same as today; translations
self-heal on the next view, review runs are reaped by the timeout guard
— unchanged trade-off, worth a sentence in docs/development.md.

## Dependencies

- Blocked by: [70] (async clients and converted callees).
- Blocks: [73], [75].

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] New setting documented in `docs/development.md` env table
- [ ] Before/after run wall-clock recorded in this issue's Log
