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

- [ ] No sync OpenAI/DeepSeek call remains anywhere in the request path.
- [ ] With one slow (mocked, delayed) generation in flight, concurrent
      cached asks and `/health` respond fast — covered by a test using a
      delayed async mock.
- [ ] Ask flow behaviour unchanged: cache tiers, quota spent only on
      cache miss, off-topic decline not saved, duplicate handling,
      generation metadata recorded.
- [ ] [68] stage timings re-recorded in the Log; the concurrency probe
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

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Frontend untouched (`npm test` etc. still green in CI)
- [ ] `docs/api.md` (AI flow) checked; update only if wording drifted
- [ ] Before/after numbers in this issue's Log
