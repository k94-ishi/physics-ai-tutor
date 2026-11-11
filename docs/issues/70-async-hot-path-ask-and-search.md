---
title: "[70] Asynchronize the hot path: /ai/ask and similarity search, async LLM clients"
labels: [backend, async, performance]
milestone: M1 Student value
priority: P1
---

**Priority:** P1  **Milestone:** M1 — Student value  **Track:** [67]

## Summary

Convert the slowest, most-used path end to end: `POST /ai/ask` and the
similarity-search reads, including both LLM clients (`AsyncOpenAI` for
OpenAI embeddings and DeepSeek chat). After this, a DeepSeek generation
no longer occupies a server thread, so slow asks stop delaying everyone
else's requests.

## Motivation

This is where the latency problem actually lives: an uncached ask holds
one of ~40 threads for the whole DeepSeek completion (tens of seconds).
A handful of simultaneous asks plus background work can exhaust the pool
and stall even cached answers and `/health` ([67] findings). Converting
this one vertical slice removes most of the thread starvation while the
rest of the app stays sync.

## Scope

The `/ai/ask` and search slice, converted whole:

- `core/openai.py`, `core/deepseek.py`: `AsyncOpenAI` clients (same
  env vars and settings; explicit request timeouts while here).
- `deepseek_service`, `embedding_service` (incl. the query-embedding
  cache [49]), `rag_service`, `ai_service.ask` and its helpers,
  `question_read_service.find_cached_answer`, `ask_history_service`.
- Routers: `api/v1/ai.py`; the search paths of `api/v1/questions.py`
  (`search_questions`, exact match) and their repositories
  (`embedding_repository`, `query_embedding_repository`, the question
  read queries they need).
- The rate-limit dependency (`enforce_ai_ask_rate_limit`,
  `rate_limit_service`, `rate_limit_repository`) — it runs on every ask.
- `ai_service.post_generation_tasks` becomes an async function so
  `BackgroundTasks` runs it on the event loop, which means the services
  it calls (`question_translation_service`, `translation_service`,
  `ai_review_service.review_question`) convert here too, as callees.
  Run orchestration and scheduling stay as they are until [72].
- Callers that must keep working: `eval_prompts` and `translate_missing`
  CLIs wrap the now-async services with `asyncio.run` (no behaviour
  change); conftest's mocked `create_embeddings` / `translate_qa` /
  DeepSeek patches become async mocks.

## Acceptance criteria

- [x] No sync OpenAI/DeepSeek call remains anywhere in the request path.
- [x] With one slow (mocked, delayed) generation in flight, concurrent
      cached asks and `/health` respond fast — covered by a test using a
      delayed async mock.
- [x] Ask flow behaviour unchanged: cache tiers, quota spent only on
      cache miss, off-topic decline not saved, duplicate handling,
      generation metadata recorded.
- [x] [68] stage timings re-recorded in the Log; the concurrency probe
      shows the starvation case gone.

## Out of scope

- Streaming ([71]).
- Parallelising background work ([72]).
- The admin, auth, users, concepts and remaining question routes ([73]).

## Technical notes

The slice must not call sync repositories from async services (no
`run_in_executor` bridges — convert the callee instead). Mind the
IntegrityError race paths (`embed_query` cache insert, duplicate
question save): same handling, now under `AsyncSession`. The off-topic
sentinel logic and prompt library are untouched — prompt `version`s do
not change, so no fingerprint updates and no prompt eval needed.

## Dependencies

- Blocked by: [69].
- Blocks: [71], [72], [73].

## Definition of done

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] Frontend untouched (`npm test` etc. still green in CI)
- [x] `docs/api.md` (AI flow) checked; update only if wording drifted
- [x] Before/after numbers in this issue's Log

## Log

### 2026-11-11 — done

554 tests pass (was 550), ruff and mypy clean, frontend untouched. The
ask path, the vector search and both LLM clients are async end to end.

**The result, measured the same way as [68]** (local stack, fake
upstream with a fixed 20 s generation, 60 concurrent asks in flight
while cheap requests are probed one at a time):

| | before [70] | after [70] |
| --- | --- | --- |
| `/health` p95 under load | 15555 ms | **1.6 ms** |
| `/health` max under load | 21191 ms | **6.9 ms** |
| cached ask p95 under load | 19019 ms | **9.8 ms** |
| 40 sequential health checks | 56.8 s wall | **0.04 s wall** |
| 60 concurrent asks, wall | 83.6 s | 50.5 s |

The starvation is gone: a liveness check behind a 21 s wait is now
1.6 ms at p95. 12 concurrent asks complete in a single 20.6 s wave,
confirming generations overlap rather than queueing.

**The next bottleneck, now visible.** 60 concurrent asks still take
50.5 s rather than one ~21 s wave. It is not the upstream (the fake
server alone serves 60 concurrent in 21.1 s) and not the thread pool any
more. It is the **15-connection database pool**, whose biggest consumer
is the background translation: `translate_missing` wraps translate *and*
embed in one transaction, so each one holds a connection for its entire
~20 s LLM call, and 60 of them starve the asks' own short database
phases. This was always true but invisible while threads capped
concurrency at a lower number — [68]'s "the pool is not the bottleneck"
was correct for the sync code and is now out of date. [72] (background
work off the request path) and [74]/[79] (pool sizing) are where this
belongs; it is not a regression, since the same load was strictly worse
before.

**Shape of the conversion.** Shared functions gained an `async_` twin
rather than being rewritten, because the admin and CLI callers are still
sync: 10 repository functions, and the service seams in
`embedding_service`, `deepseek_service`, `translation_service`,
`question_translation_service`, `question_read_service`,
`ask_history_service`, `rate_limit_service`, `question_write_service`
and `ai_review_service`. `ai_service` and `rag_service`'s generation
path converted outright, having no other callers. Where a twin would
have duplicated a rule, the rule was extracted and is now shared by
both: `_status_conditions` (the filter that keeps REJECTED answers out
of the ask cache), `_similar_embeddings_select`, `_names_by_question`,
`_review_to_store`, `_skip_reason`. A filter drifting between two copies
would be a security bug, not a style problem.

**A real bug the conversion exposed.** `test_reviewer_failure_does_not_
break_translation` failed with `MissingGreenlet`: when the reviewer
raises, `async_transaction` rolls back, which expires the ORM row, and
the error log then reads `question.id` — implicit IO, which an
`AsyncSession` refuses. So the *error handler* crashed instead of
logging. `async_review_question` now captures its scalars before the
transaction. This is precisely the lazy-loading trap flagged in [69],
and it will recur in [73]; the rule is written in docs/development.md.

**Request timeouts added** while touching the clients: the OpenAI SDK
defaults to 10 minutes, long enough to look like a hang. 30 s for
embeddings, 180 s for chat (a long answer legitimately takes tens of
seconds). [79] will make them settings.

**CLIs needed no `asyncio.run` wrapping** after all, contrary to the
plan above: keeping the sync twins means `eval_prompts`,
`review_pending` and `translate_missing` still call the sync functions
unchanged. [73] will wrap them when the twins go.

**Deviation from scope.** `/exact-match` was listed but is *not*
converted. It makes no LLM call — it is an indexed lookup that holds a
thread for milliseconds — and converting it means converting
`question_presentation_service`, which every read path shares. That is
[73]'s slice, and pulling it in here would have made this change a
read-path conversion too.

**Tests.** `tests/test_async_hot_path.py` drives the app over an async
transport, since `TestClient` cannot express concurrency. Two parked
tests assert cheap requests are served while a generation or embedding
is pending (deterministic, no timing assertions); one timing test
asserts 12 concurrent generations overlap. Only the last one actually
detects a blocked event loop — verified by swapping `asyncio.sleep` for
`time.sleep` in the stub, which makes it and only it fail. The first
version of the parked tests had a timing assertion that looked like
proof but passed even against a blocking stub, because it measured after
the block had elapsed; it was replaced rather than kept as decoration.

The 65 existing patch sites for `deepseek_service.generate_answer` now
go through `conftest.patch_generation`, which installs one sync stub on
both seams. Patching only one leaves the other pointing at the real API
— which is how the first suite run failed, with 115 authentication
errors rather than anything obvious.

`tests/test_architecture.py` pins the exact set of modules that still
touch a sync LLM client (`deepseek_service`, `embedding_service`), so a
new sync caller fails the suite. The assertion is an equality, not a
subset, so the list cannot quietly grow.
