---
title: "[76] Batch embedding calls: one OpenAI request per import, not two per row"
labels: [backend, performance]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67]

## Summary

Import, update and AI-answer paths embed one question at a time: each
`embed_language` call sends its own OpenAI request, so a bilingual row
costs two requests and a 100-row import costs 200. The OpenAI embeddings
endpoint takes a list — batch per import instead.

## Motivation

Found by a coworker's review (2026-11-11) and confirmed:
`question_write_service.import_questions_from_jsonl` loops rows, then
languages, calling `embed_language` (line 148), and each call does its
own `create_embeddings([question_text, answer_text])`. The admin
"Upload" page therefore waits on 2N sequential network round trips,
each with full latency, where one request per batch would do.

[66] already removed the N+1 *database* round trips on this path; the
API round trips were not touched (the seed hides them, because it serves
preloaded vectors and calls OpenAI never). This is the remaining half.

## Scope

- Give `embedding_service` a batch entry point that takes many texts
  across many questions/languages, chunks them to one request per chunk
  (respect the API's per-request input limit), and keeps the existing
  preloaded-vector shortcut so the offline seed still calls nothing.
- Rework `import_questions_from_jsonl` to collect every text needing an
  embedding first, fetch them in one batch, then write the rows (bulk
  insert, as [66] did for the database side).
- `translate_into`'s embedding of the newly translated text can join the
  same batching helper where a caller has several at once (a backfill, a
  multi-language fill); a single row's translation stays one call.
- Keep `delete_by_question_id`-then-insert semantics per language so a
  re-embed still replaces cleanly.
- Measure a 100-row import before and after with the [68] timings.

## Acceptance criteria

- [x] A 100-row bilingual import makes a small, bounded number of OpenAI
      requests instead of ~200 — asserted by counting calls on the mock.
- [x] Stored vectors identical to the per-row path (same model, same
      text, same `vector_key`), so `seed_embeddings.jsonl.gz` round trips
      unchanged.
- [x] The offline seed still makes zero OpenAI calls
      (`test_seed.py` guarantees preserved).
- [x] Import stays all-or-nothing on duplicate text.

## Out of scope

- DeepSeek batching: DeepSeek has no Batch API (checked 2026-10-30,
  docs/development.md), so answer generation and review calls cannot be
  batched — [72] parallelises those instead.
- Changing the embedding model or vector dimensions.

## Technical notes

Chunk by both count and total input size; a long answer plus a long
question can be large. On a chunk failure the whole import should fail
cleanly (it is already all-or-nothing), not half-embed. Order matters:
the returned vectors must be mapped back to (question, language,
question-vs-answer) by index — keep that mapping explicit and tested,
since a silent off-by-one would mis-embed every row.

## Dependencies

- Blocked by: none for correctness; easier after [70] (async client
  makes the batch call a single await). Can also land before it.
- Blocks: nothing.

## Definition of done

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] Call-count assertion in the import test
- [x] Before/after import timing in this issue's Log

## Log

### 2026-11-14 — done

612 tests pass (608 + 4 new); ruff and mypy clean; frontend untouched.
2 production files, 2 test files.

**What changed.** `embedding_service.embed_many` (and `async_embed_many`
for [94]) takes any number of texts, splits them into chunks of at most
256 items and about 200,000 characters, and calls `create_embeddings`
once per chunk, so the preloaded seed vectors and the test seam apply
unchanged. The result keeps input order; the mapping back to
(row, language, question-or-answer) is explicit in
`question_write_service._embed_provided_texts` and tested.

Import now collects every provided text first and embeds them **before
its transaction opens**, then writes the rows and their embedding rows.

**The number** (the owner asked for the simple measure, not a real-API
timing): a 100-row bilingual import went from **200 OpenAI requests to
2**, asserted by counting calls on the mock. Each request's latency is
roughly fixed, so the wall time of the embedding phase shrinks by about
the same factor; a real-API timing was not taken.

**Unchanged on purpose.**

- Stored vectors are the same: same model, same exact text per
  embedding row, so `seed_embeddings.jsonl.gz` round-trips as before and
  the offline seed still makes zero OpenAI calls (`test_seed.py`).
- Import is still all-or-nothing: the duplicate check and the single
  transaction are as they were; an embedding failure now happens before
  the transaction and inserts nothing.
- Rows missing a language are still translated one by one inside the
  transaction, and APPROVED rows still extract concepts there. So the
  [82] allowlist still names `import_questions_from_jsonl`; that entry
  goes when [94] converts import and moves those calls out too. This
  issue's text had expected the batch shape alone to remove it; it does
  not, because of those two remaining calls.
