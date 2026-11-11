---
title: "[68] Latency baseline: stage timing logs and recorded numbers"
labels: [performance, backend, observability]
milestone: M1 Student value
priority: P1
---

**Priority:** P1  **Milestone:** M1 — Student value  **Track:** [67]

## Summary

Before changing anything, make latency visible: log how long each stage
of a slow request takes (cache lookup, embedding, vector search, LLM
call, save), and record baseline numbers for the key endpoints under
no load and under modest concurrency. Every later step in [67] is
judged against these numbers.

## Motivation

`RequestLoggingMiddleware` already logs the total per-request time, but
a 20-second `/ai/ask` log line cannot say whether the time went to
DeepSeek, to the embedding call, or to the database. Without a split we
cannot tell which conversions in [67] paid off, and we risk "improving"
a stage that was never the problem.

## Scope

- A small timing helper (e.g. `core/timing.py`): a context manager that
  logs `Stage finished: name=<stage> duration_ms=<x>` with the request
  path. Standard logging only — no new dependency, no new table.
- Instrument the stages of:
  - `POST /ai/ask`: tier-0 cache lookup, `embed_query` (cache hit or
    OpenAI), vector search, DeepSeek generation, row save.
  - `GET /questions/search` and `?similar=`: embedding, vector search.
  - Background: one log line per `translate_into` (translation ms,
    embedding ms) and per AI-review item.
- A small concurrency probe in `scripts/` (plain Python, asyncio +
  httpx-style stdlib or whatever the repo already has): fires N
  concurrent requests at a *local* stack and prints p50/p95. It must
  default to `http://localhost:8000` and refuse non-local URLs, so it
  can never be pointed at production by accident.
- Record the baseline in this issue's Log: cached ask, uncached DIRECT
  ask, uncached RAG ask, similarity search — each alone and with 10/40
  concurrent cached asks in the background (the thread-pool starvation
  case the track is about).

## Acceptance criteria

- [x] One slow `/ai/ask` can be fully explained from the logs: the sum
      of its stage lines roughly matches the middleware's total (99.7 %).
- [x] Baseline table committed in this issue's Log with the date and
      commit hash.
- [x] The probe script refuses a non-localhost base URL.
- [x] No behaviour change; no new dependency.

## Out of scope

- Metrics infrastructure (Prometheus, OpenTelemetry). Logs are enough at
  this scale; revisit if the project ever gets a metrics stack.
- Any fix. This issue only measures.

## Technical notes

Timing wrappers belong in services, not routers (`test_architecture.py`
layering stays untouched). DeepSeek durations in production also depend
on the off-peak window and context caching (docs/development.md, pricing
notes) — note the time of day next to any recorded number. The existing
`test_logging.py` shows how middleware logs are asserted; add one test
that a stage line is emitted (with the LLM mocked).

## Dependencies

- Blocked by: none. Do first in Track F ([67]).
- Blocks: meaningful before/after claims in [69]–[74].

## Definition of done

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] Baseline numbers recorded in the Log
- [x] `docs/development.md` gains a short "reading latency logs" note

## Log

### 2026-11-11 — done; baseline recorded

Shipped `core/timing.py` (`stage()` / `request_path()`), stages on the
ask path, the search path and the background bodies,
`scripts/latency_probe.py`, `scripts/fake_llm_server.py`, and
`tests/test_timing.py` (10 tests). Suite 541 passed, ruff and mypy clean.

**Method.** Measuring against the real DeepSeek would make generation
time a variable and spend quota, so the backend ran against
`fake_llm_server.py` with a fixed 20 s chat delay and 0.3 s embedding
delay. Generation time is therefore a known constant and every number
below is reproducible without an API key. Host-run uvicorn (one worker,
`ENVIRONMENT=production`), local pgvector on port 5437, the 144-question
seed (576 embedding rows), macOS, commit feb9d2d + this work.

Two caveats on these numbers. The fake embeddings are random vectors, so
RAG retrieval returns nothing above the 0.5 similarity threshold
(`rag_context count=0`) — stage *durations* are representative, context
*size* is not. And real DeepSeek latency varies with load and the
off-peak window, so the 20 s is a stand-in for "a slow call", not a
measured production figure. Numbers needing the real key are listed at
the end.

**Idle (one request at a time).**

| What | p50 | p95 | max |
| --- | --- | --- | --- |
| `GET /health` | 0.6 ms | 0.8 ms | 0.9 ms |
| `GET /questions` (list) | 76.9 ms | 97.0 ms | 106.5 ms |
| `POST /questions/search`, embedding cache miss | 680 ms | — | — |
| `POST /questions/search`, cache hit | 7.3 ms | 23.9 ms | 24.6 ms |
| `POST /ai/ask`, tier-0 cache hit | 4.4 ms | 9.0 ms | 9.1 ms |
| `POST /ai/ask`, uncached (20 s generation) | 20507 ms | — | — |

The query-embedding cache ([49]) is worth **680 ms → 7 ms** on a repeated
search. The tier-0 ask cache is worth **20.5 s → 4 ms**. Both already
pay for themselves; nothing in this track should weaken them.

**Stage breakdown of one uncached RAG ask** (total 20913 ms):

| Stage | ms | Note |
| --- | --- | --- |
| `ask_cache_lookup` | 6.3 | miss |
| `rag_context` | 394.5 | contains the two below |
| ├ `embed_query` → `openai_embeddings` | 336.8 | cache miss |
| └ `vector_search` | 40.0 | 576 rows, no index |
| `deepseek_chat` | 20033.7 | **96 % of the request** |
| `save_answer` → `openai_embeddings` | 420.2 | embeds the saved row |
| accounted for | 20854.8 | 99.7 % of the total |

The remaining ~58 ms is routing, auth and serialisation. Acceptance
criterion met: a slow ask needs no guesswork.

**Under concurrency — the starvation this track is about.**

60 concurrent uncached asks, while probing cheap endpoints one at a time:

| What | idle p50 | under load p50 | under load p95 | under load max |
| --- | --- | --- | --- | --- |
| `GET /health` | 0.6 ms | 0.7 ms | **15555 ms** | **21191 ms** |
| `POST /ai/ask` (cache hit) | 4.4 ms | 9.0 ms | **19019 ms** | **19869 ms** |

40 sequential health checks took **56.8 s** of wall clock instead of
~0.03 s. The distribution is bimodal, which is the thread pool exactly:
a request either finds a free thread (sub-millisecond) or waits for a
whole 20 s generation to release one. A liveness check behind a 21 s
wait is also what would make a platform mark the service unhealthy.

The 60 asks themselves: p50 21.5 s, p95 83.2 s, wall 83.6 s — about four
waves of 20 s rather than one.

**Why four waves, not two.** anyio's default limiter is 40 threads
(confirmed at runtime), but 60 asks produced **119 DeepSeek calls**: each
saved answer schedules a background translation, which is another ~20 s
blocking call on the *same* pool. Background work does not run beside
request handling, it competes with it, roughly halving effective
capacity. That is [72]'s case, measured.

**What is *not* the bottleneck** (checked, so later steps do not chase
it): the SQLAlchemy pool is 15 connections (size 5 + overflow 10), but a
session releases its connection at the rate-limit commit, before the LLM
call. 30 concurrent asks left `/health` at 0.5 ms p50. The pool is worth
sizing in [74], but it is not what starves the server today.

**Correction to an earlier measurement.** A first run showed 20 asks
taking two waves, which looked like a server limit. It was the probe:
`asyncio.to_thread` shares a default executor of about 12 threads, so
the measurement capped itself. The probe now sizes its own pool to `-c`;
the same check against the fake server went from 40.1 s to 20.1 s wall
for 20 concurrent 20 s requests. The percentile helper also used
interpolated quantiles, which reported a p95 above the slowest observed
request; it is nearest-rank now. Any number taken before those two fixes
should be discarded.

**Needs the real DeepSeek key, deliberately not measured.** Real
generation latency (p50/p95 by time of day, in and out of the off-peak
window), real `text-embedding-3-small` latency, and real token counts
per answer. Say the word and these can be taken against a local stack
with a real key; nothing above depends on them, because the track's
problem is *waiting*, not how long the wait is.
