---
title: "[82] Never hold a database connection across an LLM call: split the translate/embed transaction"
labels: [backend, performance, database]
milestone: M1 Student value
priority: P1
---

**Priority:** P1  **Milestone:** M1 — Student value  **Track:** [67]

## Summary

`translate_missing_languages` wraps the translation *and* the embedding
of a question in one transaction, so a pooled database connection is held
for the whole ~20 second LLM call. Split it so a connection is held for
the writes, never for the wait, and make that a rule the suite enforces.

## Motivation

Owner's point (2026-11-11): these should be separated.

[70] measured why it matters. With the request path async, the thread
pool is no longer the ceiling, and the next one appeared immediately:
60 concurrent asks took **50.5 s** instead of a single ~21 s wave. It is
not the upstream (the stand-in serves 60 concurrent in 21.1 s) and not
threads. It is the 15-connection pool, and the biggest consumer is the
background translation holding one connection per in-flight LLM call.

The shape of the bug is more general than this one function: **a
connection held across a network call to a third party is a connection
spent waiting on something the database has no part in.** Sixty
translations × 20 s against a pool of 15 is four waves of pure queueing,
and the asks' own millisecond-long database phases queue behind them.

This was true before the async work too, but invisible: threads capped
concurrency below the point where the pool ran out. Note this supersedes
[68]'s "the pool is not the bottleneck", which was measured on the sync
code and is now out of date.

## Scope

- Restructure `question_translation_service.async_translate_into` and
  `async_translate_missing_languages` (and the sync twins, so both
  behave alike until [73]) into three phases:
  1. read the source text, then **release the connection**;
  2. call DeepSeek and OpenAI with no transaction open;
  3. open a short transaction for `set_text` + the embedding rows.
- Audit the other places that may hold a connection across an LLM call
  and fix or document each:
  - `ai_review_service.async_review_question` — the `ai_review_grade`
    transaction spans the concept read, the context build *and* the
    grading call.
  - `ai_review_service.execute_run` — one transaction per question,
    which includes that question's grading call ([72] touches this).
  - `question_write_service.async_save_ai_question` — holds a
    transaction across `async_embed_language`'s OpenAI call.
  - `concept_service` extraction paths called from admin writes.
- Add an architecture test for the rule: no `await` of an LLM seam
  inside a `transaction(...)` / `async_transaction(...)` block. The
  seams are a short list (`deepseek_service`, `embedding_service`,
  `translation_service`, `concept_service`), so this is checkable with
  the same AST approach as the other layering rules.
- Re-measure the [70] case (60 concurrent asks) and record the number.

## Acceptance criteria

- [x] No transaction spans a call to OpenAI or DeepSeek on any converted
      or background path; the architecture test fails on a new one. Four
      sync admin write paths remain as a pinned, shrinking allowlist
      ([73]/[76]) — see the Log.
- [x] Behaviour unchanged: a translation that fails still leaves the row
      untranslated and never raises; a partially translated row is never
      committed with text but no embeddings.
- [x] 60 concurrent asks complete in roughly one generation wave rather
      than four, measured with `scripts/latency_probe.py` and the fake
      upstream, recorded in the Log.
- [x] Connection count during a translation backlog stays well under the
      pool size (one non-idle connection observed).

## Out of scope

- Pool sizing ([74]) and worker count ([75]) — this issue removes the
  demand rather than raising the supply, which is the right order.
- Running translations concurrently ([72]). That multiplies the demand,
  so it should land after this.

## Technical notes

Splitting the transaction changes the failure window: today a crash
between translating and embedding rolls both back, whereas afterwards a
row could carry text with no embeddings. Keep that impossible by writing
the text and its embeddings in the *same* final transaction — only the
LLM calls move out, not the writes. The embedding call must therefore
happen before that transaction opens, on text held in memory.

`translate_missing` loops languages per question; with the transaction
moved inside, each language becomes its own short write. That is fine -
`[53]`'s guarantee is "a translated row never reaches the queue again",
not "all languages appear atomically".

## Dependencies

- Blocked by: none. Independent of [71].
- Blocks: [72] should land after this, so concurrency multiplies a fixed
  pattern rather than a broken one.
- Supersedes: the "not the bottleneck" note in [68]'s Log.

## Definition of done

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] Architecture test added
- [x] Before/after concurrency numbers in this issue's Log
- [x] `docs/development.md` carries the rule next to the other layering
      rules

## Log

### 2026-11-11 — done

578 tests pass (was 569); ruff and mypy clean.

**The number.** Same scenario as [68]/[70]: local stack, fake upstream
with a fixed 20 s generation, 60 concurrent asks.

| | before [70] | after [70] | after [82] |
| --- | --- | --- | --- |
| 60 concurrent asks, wall | 83.6 s | 50.5 s | **21.4 s** |
| 60 concurrent asks, p95 | 83.2 s | 50.5 s | **21.4 s** |
| non-idle connections during the wave | — | dozens | **1** |
| `/health` p95 during | 15.6 s | 1.6 ms | 0.6 ms |

One generation wave, as fast as the upstream allows. All 120 LLM calls
(60 generations + 60 background translations) completed; the
translations now overlap too, holding no connection during their LLM
phase.

**The shape.** `question_translation_service` is split into
`prepare_translation` (translate + embed the pair; takes no session) and
`apply_translation` (text and embeddings written together in one short
transaction, so a row can never carry text without vectors). The
transaction-owning entry point `translate_missing_languages` reads in a
short committed transaction, prepares with the connection released, and
applies per language — per-language commits are fine, since [53]'s
guarantee is that a translated row never re-enters the queue, not that
both languages appear atomically. `translate_into` survives for callers
that already own a transaction (the all-or-nothing import).

**The audit found two things the issue had not listed.**

1. `question_read_service.fetch_question` — the *student detail page* —
   lazily translates a pre-bilingual row inline, and did so while
   holding a connection. Now prepare/apply. The student still waits for
   the translation (that is [53]'s design); the pool no longer waits
   with them.
2. The sync `save_ai_question` had no callers left since [70] — only
   its own tests. Deleted, tests migrated to the async version, which
   now embeds before its transaction. A duplicate save therefore costs
   one embedding call it did not before; rare (the ask flow already
   checked the cache for that exact text) and cheaper than every save
   holding a connection through OpenAI.

Also fixed on the way: `embed_query`'s cache-miss path called OpenAI
with the lookup's transaction still open, on both the sync and async
sides; the RAG context reads sat open through the whole generation
(including the streamed one, where the stream keeps the response open
for the entire answer); and the review grade transaction spanned the
grading call in both variants.

**One design decision surfaced by a failing probe.** The direct ask
relied on the quota-recording *callback* committing to release the
cache-lookup connection before generation. The probe stubs the callback
and caught it. The lookup now commits for itself: connection discipline
must not depend on a side effect of someone else's bookkeeping.

**Enforcement, two layers.**

- `test_architecture.py::test_no_transaction_spans_an_llm_call` —
  lexical tripwire over a named list of LLM-calling functions, with a
  pinned allowlist of four sync admin write paths (`create_question`,
  `update_question`, `import_questions_from_jsonl`,
  `reextract_concepts_for_questions`) that keep their transaction by
  design until [73]/[76]; a companion test fails if an allowlist entry
  stops matching, so the list can only shrink deliberately.
- `tests/test_llm_connection_discipline.py` — six runtime probes that
  patch each LLM seam with a stub recording
  `session.in_transaction()` at the moment of the call: translation,
  failed translation (commits nothing), direct ask, RAG ask, query
  embedding miss, review grading.

`execute_run` (review runs) was left structurally as is: since the
grade's reads now commit first, the run loop's connection is released
before each grading call at runtime, and [72] reworks that loop anyway
when it adds concurrency.

**A measurement goof worth recording.** The first "after" run reported
60 asks in 0.2 s — every one a cache hit, because the shared dev
database already contained rows with my probe text, created by a
parallel session on this machine. The real run salts the question text
with a timestamp. Checking *why* a number is impossibly good is part of
taking the number.
