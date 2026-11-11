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
- Holding a connection across the LLM call is **[82]**, split out at the
  owner's request (2026-11-11). It lands *before* this issue: running
  translations concurrently multiplies connection demand, so the
  per-translation pattern has to be fixed first.

## Acceptance criteria

- [x] No `threading` primitives left in services (process-local claim
      state remains until [75] replaces it); enforced by an architecture
      test.
- [x] A review run with delayed mock calls finishes ~K times faster than
      sequential, with correct counts, token totals and heartbeat.
- [x] A run that is reaped mid-flight stops its remaining items ([34]
      semantics), covered by a test.
- [x] Translation claims still prevent duplicate work under concurrency.
- [x] Daily budget never exceeded, including at run start under
      concurrency — unchanged, since the budget is spent at `start_run`
      when the question list is fixed, before any concurrency exists.

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

- Blocked by: [70] (async clients and converted callees), and [82] (fix
  the connection-per-LLM-call pattern before multiplying it).
- Blocks: [73], [75].

## Definition of done

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] New setting documented in `docs/development.md` env table
- [x] Before/after run wall-clock recorded in this issue's Log

## Log

### 2026-11-12 — done

588 tests pass (was 578); ruff and mypy clean.

**The numbers**, measured against a stand-in upstream with a fixed 5 s
call, on a private database so a parallel session could not disturb it:

| | sequential | K=3 | K=6 |
| --- | --- | --- | --- |
| AI review run, 12 questions | 61.6 s | **20.4 s** | **10.2 s** |
| Background translation, 9 rows | 47.8 s | **16.0 s** | — |

Exactly linear: 3.0x at K=3 and 6.0x at K=6, with all items completing
(`reviewed=12`, `translated=9/9`). A nightly run of 200 questions goes
from over an hour to about twenty minutes at the default of 3.

**What changed.** All four `add_task` targets are coroutine functions
now; the last two (`translate_missing`, `translate_concept_names`) and
the review runner were converted here. Items run under an
`asyncio.Semaphore` sized by `AI_REVIEW_CONCURRENCY` /
`TRANSLATION_CONCURRENCY`, both defaulting to 3, and **each concurrent
item opens its own session** — a session cannot be shared between tasks
running at once, which is the one way this change could have corrupted
data rather than merely being slow.

The run row is updated from a single place under an `asyncio.Lock`, so
progress polling still sees counts climb and two items never write the
row at once. Token counts are read inside each item's own session and
carried out as plain integers (`ItemResult`), so the run bookkeeping
never touches a detached ORM row — the [70] lesson applied up front.

The `threading.Lock` is gone: claim and release never await between
reading and writing the in-flight set, so on one event loop no lock is
needed. **This is still process-local** and [75] remains the fix for
multiple workers; an architecture test now forbids `threading` in
services so the distinction cannot blur.

**Takeover ([34]) under concurrency.** The status is re-checked per item
rather than once per run, so a reaped run stops its queue instead of
only its next item. Items already past that check do finish — with K
slots, up to K-1 extra grading calls can land after a takeover. That is
inherent to running several at once and is the reason to keep K small;
the test pins the bound (`<= 4` of 8 at K=2) rather than asserting the
vaguer "fewer than all".

**Two things found while doing this.**

1. `concept_service.translate_missing_name` held a connection across its
   LLM call — the same [82] fault, missed because the call is not
   lexically inside a `with transaction(...)` block, only inside an
   implicit one opened by the preceding reads. Fixed in both variants.
   Worth noting the lexical tripwire cannot see this shape; the runtime
   probes are what would catch it.
2. Two tests started passing **vacuously**: they called the
   now-coroutine `translate_missing` without awaiting it, so the body
   never ran and "the row stays untranslated" was trivially true.
   Running the suite with `-W error::RuntimeWarning` surfaced them; both
   are async now, and the skip test additionally asserts the claim is
   released so an unapproved row can be picked up once it is approved.

**The stand-in upstream** learned to answer translation prompts with the
marker format the parser expects. Before that every translation in a
local measurement failed as "skipped", which made the translation
numbers meaningless — the same gap noted in [71]'s log, now closed.
