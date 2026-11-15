---
title: "[67] Track F: asynchronize the backend and cut latency"
labels: [epic, roadmap, performance, async]
milestone: M1 Student value
priority: P1
---

**Priority:** P1  **Milestone:** M1 — Student value

Owner's request (2026-11-11): make the whole system asynchronous and
improve latency. This track turns that into ordered, independently
mergeable steps. Like Track E, every step keeps the API, the database
and the screens behaviourally identical unless the step's own issue says
otherwise (only [71] streaming changes what a student sees).

Revised 2026-11-11 after a coworker's review: it confirmed the streaming
and serial-AI-review findings already in the table below, and added
three that were missing — per-row embedding calls on import ([76]), the
question page's serial request wave ([77]), and the process-local
background claim that blocks running more than one worker ([75]). The
last one is the important one: it is a latent correctness bug today, and
it is what stands between the project and the cheapest throughput fix
there is.

## Review findings (2026-11-11, measured on commit feb9d2d)

| Area | Finding | Evidence |
| --- | --- | --- |
| Routes | Every route is sync (`def`), so FastAPI runs each request on the anyio thread pool (default 40 threads per process) | `api/v1/*.py`; only middleware and error handlers are `async` |
| LLM calls | DeepSeek answer generation (tens of seconds) and OpenAI embeddings run blocking inside a request thread | sync `OpenAI` clients in `core/openai.py`, `core/deepseek.py`; `deepseek_service._request` |
| Background work | `BackgroundTasks` with sync functions also run on the same 40-thread pool: post-ask translate+review (`ai_service.post_generation_tasks`), list translations (`background_translation_service`), and whole AI review runs (`admin.py:128`) | a run of 50 questions holds one thread for many minutes |
| Consequence | ~40 concurrent slow operations (asks, translations, a review run) exhaust the pool; then even `/health` and cached asks queue behind them | single uvicorn process on Render, no `--workers`. **Measured in [68]**: under 60 concurrent asks, `/health` p95 went from 0.8 ms to 15.6 s (max 21.2 s) and a cached ask from 9 ms to 19.0 s |
| Background competes with requests | Each saved answer schedules a ~20 s translation on the same 40-thread pool, so 60 asks became 119 blocking calls and four waves instead of one — effective capacity roughly halves | [68] measurement; [72] fixes it |
| Not the bottleneck | The SQLAlchemy pool is 15 connections, but a session releases its connection at the rate-limit commit, before the LLM call; 30 concurrent asks left `/health` at 0.5 ms p50. Worth sizing ([74]), not the cause | [68] |
| DB | Sync engine (`create_engine`, psycopg). SQLAlchemy 2 supports async on the same `postgresql+psycopg://` URL via `create_async_engine`, so no new driver and no `DATABASE_URL` change | `database/database.py` |
| Perceived latency | `/ai/ask` returns one JSON blob after the full DeepSeek completion; the student watches a spinner for the whole generation | `api/v1/ai.py`, `frontend/src/lib/api/ai.ts` |
| Sequential external calls | Background translation handles questions one by one; an AI review run reviews one question at a time (a 200-question run is 200 back-to-back calls, over an hour); `translate_into` does translation then embedding serially | `background_translation_service.translate_missing`, `ai_review_service.execute_run` |
| Per-row embedding calls | Import embeds row by row: `embed_language` makes its own OpenAI request, so a bilingual row costs 2 requests and a 100-row import ~200, where one batch per chunk would do | `question_write_service.import_questions_from_jsonl:148` |
| Scaling out is blocked | Background de-duplication is a module-level set behind a `threading.Lock`, so it only holds inside one process; two uvicorn workers would translate the same row twice. The AI review guard, by contrast, is database-backed and correct | `background_translation_service._in_flight`; contrast `ai_review_run` partial unique index |
| Question page waves | Three requests per question page; related and prerequisites already run in parallel, but both wait on the detail response although neither needs it | `components/QuestionDetail.tsx:66` then `:92` |
| Vector search | No pgvector index (no HNSW/IVFFlat migration exists); every similarity search is a sequential scan. Harmless at ~150 rows, a real cost at thousands | `alembic/versions/`, `models/embedding.py` |
| Measurement | `RequestLoggingMiddleware` logs total ms per request, but nothing splits a slow ask into cache lookup / embedding / vector search / DeepSeek time | `core/logging.py` |
| Tests | 522 backend tests use the sync `TestClient` (fine with async routes) but service/repository tests take a sync `Session` directly; conftest mocks (`create_embeddings`, `translate_qa`, ...) are sync functions | `tests/conftest.py` |

What is in good shape and must not be lost: the layering rules
(`test_architecture.py`), `transaction()` as the only commit point, the
query-embedding cache ([49]), the tier-0 ask cache, the AI-review budget
and overlap guard ([25]/[34]), and the offline test suite.

## Why async, in one paragraph

The server spends almost all of its time waiting on OpenAI, DeepSeek and
PostgreSQL. Today each wait occupies one of 40 threads; when they are
gone, every user waits, however cheap their request is. On an async
stack a wait costs (almost) nothing, so slow LLM calls stop delaying
fast requests, background work stops competing with requests for
threads, and independent external calls can run at the same time.
Latency for a single quiet request barely changes; latency under any
real concurrency improves a lot, and streaming ([71]) cuts the felt
wait for the slowest endpoint from "whole answer" to "first words".

## Order (each step is a separate, independently mergeable PR)

1. ~~[68] Latency baseline: per-stage timing logs and recorded numbers~~
   done 2026-11-11 (stage logs, probe + fake-LLM scripts, baseline table)
2. ~~[69] Async foundation: async engine/session/`transaction()`, test
   plumbing, one small route converted as proof~~ done 2026-11-11
   (adds greenlet via `sqlalchemy[asyncio]`; conventions in
   docs/development.md, "Two stacks during the async migration")
3. ~~[70] Hot path: `/ai/ask` and similarity search go async end to end,
   with `AsyncOpenAI` clients for both providers~~ done 2026-11-11
   (`/health` p95 under load 15.6 s -> 1.6 ms; `/exact-match` deferred to
   [73], and the database pool is now the next limit)
4. ~~[71] Streaming `/ai/ask` (SSE): the student reads the answer while
   it generates~~ done 2026-11-11 (first text at 0.79 s against a 10.9 s
   answer; the client falls back to `/ai/ask` if a proxy buffers)
5. ~~[82] Never hold a database connection across an LLM call (owner,
   2026-11-11)~~ done 2026-11-11 (60 concurrent asks: 50.5 s -> 21.4 s,
   one generation wave; enforced by an architecture test plus runtime
   probes)
6. ~~[72] Background work on the event loop: asyncio tasks, parallel
   translations, bounded concurrency inside AI review runs~~ done
   2026-11-12 (3.0x at K=3, 6.0x at K=6, exactly linear; a 200-question
   nightly run goes from over an hour to about twenty minutes)
7. ~~[75] Worker-safe background claims: de-duplication moves into the
   database, then run more than one worker~~ done 2026-11-12 (a
   `background_claims` table; eight racing processes yield one winner;
   two workers is the ceiling until [73] halves the pools per worker)
8. [73] Convert everything that remains; the app keeps no sync engine.
   Slice 1 (auth, users, sessions) merged 2026-11-12; the rest was
   **re-scoped on 2026-11-13 into small issues**, each its own PR, after
   a one-pass attempt proved too big to merge ([73]'s Log):
   1. ~~[83] public question reads (list, detail, exact match, related,
      prerequisites) - also makes an un-awaited coroutine a test failure~~
      done 2026-11-13 (601 tests; no regression at concurrency 8)
   2. ~~[84] Asynchronize the public tag search (GET /concepts)~~ done 2026-11-13
   3. ~~[89] Asynchronize the admin tag editor reads: list and detail~~ done 2026-11-13
   4. ~~[90] Asynchronize the admin tag editor writes: gloss, words, merge, split~~ done 2026-11-13
   5. ~~[91] Asynchronize concept extraction and the re-extract route~~ done 2026-11-13
   6. ~~[85] Asynchronize the review routes: review, bulk review, history~~ done 2026-11-13
   7. ~~[92] Asynchronize the fill-translations route (POST /questions/translate)~~ done 2026-11-13
   8. ~~[86] Asynchronize delete and bulk delete~~ done 2026-11-14
   9. ~~[93] Asynchronize create and update (prepare/apply)~~ done 2026-11-14
   10. ~~[94] Asynchronize JSONL import~~ done 2026-11-14 ([82] allowlist now empty)
   11. ~~[95] Seed tags step on the async services; delete the sync tag-extraction path~~ done 2026-11-14
   11a. ~~[102] translate_missing CLI on the async service; delete the sync translation half~~ done 2026-11-14
   12. ~~[87] Asynchronize the usage dashboard and the agreement report~~ done 2026-11-15
   13. ~~[96] Asynchronize the review dataset export~~ done 2026-11-15
   14. [97] Asynchronize AI review runs; one ai_review_service
   15. [88] Delete the sync engine, sync LLM clients and remaining sync twins
   16. [98] Rename pass: drop the async_ prefixes
   17. [99] Async end state: architecture test, docs, connection budget (closes [73])
   Re-split 2026-11-13 into ~10-test slices; [87] can run beside the concept chain.
9. [74] Latency quick wins independent of async: pgvector HNSW index,
   pool settings for the Supabase pooler, response compression. The
   pool numbers are best chosen after [88], when there is one pool.
10. ~~[76] Batch embedding calls on import (2 requests per row -> one per
   chunk)~~ done 2026-11-14 (100 bilingual rows: 200 requests -> 2).
11. [77] Question page: three requests in two waves become one wave.
    Independent; can run any time.
12. [100] Reuse sense embeddings in concept matching (fewer OpenAI calls
    per extraction). Independent; best after [95].

[74], [76] and [77] touch no async plumbing and can be picked up
whenever there is a gap, as long as [68] is in place to measure them.

Rules for the whole track:

- No feature changes inside a conversion PR; behaviour changes ([71])
  get their own issue.
- Convert vertical slices (router -> service -> repository), never half
  a call chain; a slice merges only with the suite green.
- Measure after each step with the [68] timings before claiming a win.
- Before each PR: pytest, ruff, mypy, lint, tsc, vitest, build (AGENTS.md).
- Production constraints: never touch the production `DATABASE_URL` or
  real API keys.
- **Deploying**: the owner deploys the whole track at once, after every
  step is finished (owner, 2026-11-11) — not step by step. So each PR
  must leave `main` deployable, and anything that can only be verified
  on the deployed stack is collected into one pre-deploy check at the
  end of the track rather than done per step. Known entries for that
  check so far: SSE is not buffered by Render's proxy ([71]), the
  pgvector index migration and pool settings on Supabase ([74]), and the
  worker count against the Supabase connection limit ([75]; [88] halves
  the per-worker demand, so re-read the budget after it). Migrations
  are applied by the owner before the backend deploy, as usual.

## Dependencies

- Independent of Track E's remaining items ([61], [65]).
- [26]'s nightly GitHub Actions run calls `review_pending`, which [97]
  wraps with `asyncio.run`; the workflow itself does not change.
