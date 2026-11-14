---
title: "[102] translate_missing CLI on the async service; delete the sync translation half"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

Split out of [95] (2026-11-14). The `translate_missing` CLI is the last
caller of the sync `translate_missing_languages`. Drive the async one
with `asyncio.run`, then delete the sync translation half.

## Scope

- `cli/translate_missing.py`: its reads and translations on
  `AsyncSessionLocal` via `asyncio.run`; output and `--dry-run`
  unchanged.
- Delete `question_translation_service.translate_missing_languages`,
  `prepare_translation`, `apply_translation`, `write_embeddings` and
  `_source_text`'s sync users; keep the async ones.
- Delete any sync twin in the translation and embedding services that
  loses its last caller (check `translation_service.translate_qa`,
  `embedding_service.create_embeddings`; the AI review run and the RAG
  path may still use them until [97]/[88]).

## Acceptance criteria

- [x] `test_cli.py`'s translate_missing tests pass on the async path.
- [x] `question_translation_service` has no sync function that touches
      a session.

## Dependencies

- Blocked by: [95]. Blocks: [88].

## Definition of done

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] Log entry in this file; `status.md`, [67] and [73] updated

## Log

### 2026-11-14 — done

614 tests pass (615 - 1: the sync `embed_many` test merged into the
async one); ruff and mypy clean; frontend untouched. 5 production
files, 6 test files.

- `translate_missing` runs on `AsyncSessionLocal` through `asyncio.run`:
  one short read lists the rows (released before any LLM call), then
  each row goes through `async_translate_missing_languages`. Output,
  `--dry-run` and the exit code are unchanged. The first version ended
  the read with a bare `rollback()`; the architecture test caught it
  (only the transaction helper may commit or roll back), so it uses
  `async_transaction` instead.
- `question_repository.get_missing_language` is async (the CLI was its
  only caller).
- **Deleted, no callers left:** `question_translation_service`'s
  `translate_missing_languages`, `prepare_translation`,
  `apply_translation`, `write_embeddings`; `translation_service.translate_qa`;
  `embedding_service.embed_many`. The translation service and the
  translator now exist once, async. The sync `create_embeddings` and
  `chat_completion` stay: the sync RAG and AI-review paths use them
  until [97]/[88].
- Tests: the CLI fixture binds only async factories now; the translator
  tests drive the real async translator; `patch_translate_qa` and the
  autouse mock patch the async seam only.
