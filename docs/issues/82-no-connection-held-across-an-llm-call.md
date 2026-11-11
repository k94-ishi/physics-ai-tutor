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

- [ ] No transaction in the codebase spans a call to OpenAI or DeepSeek;
      the new architecture test fails if one is added.
- [ ] Behaviour unchanged: a translation that fails still leaves the row
      untranslated and never raises; a partially translated row is never
      committed with text but no embeddings.
- [ ] 60 concurrent asks complete in roughly one generation wave rather
      than four, measured with `scripts/latency_probe.py` and the fake
      upstream, recorded in the Log.
- [ ] Connection count during a translation backlog stays well under the
      pool size.

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

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Architecture test added
- [ ] Before/after concurrency numbers in this issue's Log
- [ ] `docs/development.md` carries the rule next to the other layering
      rules
