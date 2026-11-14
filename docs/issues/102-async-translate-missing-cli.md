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

- [ ] `test_cli.py`'s translate_missing tests pass on the async path.
- [ ] `question_translation_service` has no sync function that touches
      a session.

## Dependencies

- Blocked by: [95]. Blocks: [88].

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Log entry in this file; `status.md`, [67] and [73] updated
