---
title: "[94] Asynchronize JSONL import"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: admin import. No behaviour change.

## Scope

- Route `POST /questions/import`, `import_questions_from_jsonl`.
- [76] is done: the provided texts are already embedded before the
  transaction. What still runs inside it is per-row translation and
  concept extraction; moving those out (prepare/apply, as [93] did for
  create) is what removes the last [82] allowlist entry.

## Acceptance criteria

- [x] Import stays all-or-nothing; per-line errors unchanged.

## Dependencies

- Blocked by: [93] (and preferably [76])
- Blocks: [95]

## Rules (all [73] slices)

- Twins only while an unconverted caller needs the sync version; delete a
  sync function in the slice that removes its last caller.
- Tests that call converted code are async on `async_db`; arrange with
  `db` and commit. Frontend untouched.
- Reference production code: `git diff 260d7c2 9c42cfd -- <paths>` on
  `wip/73-async-remaining` (its twins are collapsed; adapt, do not copy).

## Definition of done

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] Log entry in this file; `status.md`, [67] and [73] updated

## Log

### 2026-11-14 — done

614 tests pass (612 + 2 new); ruff and mypy clean; frontend untouched.
8 production files, 5 test files.

**The [82] shape.** Import reads (duplicate check), then with no
transaction open embeds every provided text in chunks ([76]), extracts
and plans concepts for APPROVED rows, and translates missing languages;
one short transaction then inserts the rows with their embeddings,
translations, concepts and levels. Still all-or-nothing: an embedding
failure inserts nothing; a failed extraction or translation skips that
row's concepts or language, as before.

**The [82] allowlist is empty.** Import was its last entry. Every path
that held a transaction across an AI call has now been split, and the
allowlist is pinned empty.

**One index for the whole import.** Planning each row separately would
let two rows that introduce the same new sense create it twice (the
sync code avoided that by flushing between rows).
`concept_service.async_prepare_concepts_many` reads the index once for
all rows and plans them in order against it. A new test covers this; it
was checked to fail when each row gets its own index copy.

**Pulled forward from [95].** The seed calls import, so it now drives the
async import through `asyncio.run` on its own `AsyncSessionLocal`; the
stored-tags step after it stays sync until [95]. The seed test forbids
the async AI seams too (`_async_request_embeddings`,
`async_extract_concept_names`, `async_translate_qa`), so "the seed makes
no AI calls" still holds rather than passing vacuously.

**Deleted, no callers left:** `embed_language`, `translate_into`,
`translate_missing`, `refresh_machine_translations` (translation
service); the sync `prepare_for_response`, `attach_concept_names`,
`attach_retrieved_questions`, `attach_ai_reviews` (presentation); the
sync `ai_review_repository.latest_for_questions`. The sync
`question_repository.create_questions` is now used only by its own
tests; left for [88].

**Tests.** 11 tests moved to async (the import tests and the three
retrieved-question tests); a runtime probe checks import's three AI
calls run with no transaction.
