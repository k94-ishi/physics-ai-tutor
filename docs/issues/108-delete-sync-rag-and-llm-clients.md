---
title: "[108] Delete the sync RAG path and the sync LLM clients"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [88] and [73]

## Summary

Second slice of [88]: the last sync calls to OpenAI and DeepSeek. No
behaviour change.

## Scope

- `rag_service.generate_rag_answer`, `retrieve_context`,
  `load_context_by_ids` (sync): reached only from tests since [106].
- Behind them, sync only through that path: `embedding_service.embed_query`,
  `search_similar_questions`, `create_embeddings`, `_request_embeddings`;
  `deepseek_service._request`, `chat_completion`, `generate_answer`;
  `query_embedding_repository.get` / `create` / `touch`;
  `embedding_repository.search_similar_embeddings`;
  `question_repository.get_questions_by_ids`;
  `question_concept_repository.get_concepts_for_questions`.
- The sync clients in `core/openai.py` and `core/deepseek.py`.
- conftest `patch_*` helpers stop installing the sync stub;
  `test_the_sync_llm_clients_are_only_used_by_unconverted_code` becomes
  "no sync LLM client exists".
- ~19 tests (13 in `test_rag_service.py`): point each at the async twin,
  or delete it where an async test already covers the same case.

## Acceptance criteria

- [ ] No sync `OpenAI` client and no sync call to either provider.

## Dependencies

- Blocked by: [107]
- Blocks: [110]

## Rules (all [73] slices)

- Twins only while an unconverted caller needs the sync version; delete a
  sync function in the slice that removes its last caller.
- Tests that call converted code are async on `async_db`; arrange with
  `db` and commit. List `async_db` before `admin_client` ([87]).
- Reference production code: `git diff 260d7c2 9c42cfd -- <paths>` on
  `wip/73-async-remaining` (its twins are collapsed; adapt, do not copy).

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Log entry in this file; `status.md`, [67], [73] and [88] updated
