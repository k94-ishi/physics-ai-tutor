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

- [x] No sync `OpenAI` client and no sync call to either provider.

## Dependencies

- Blocked by: [107]
- Blocks: [110]

## Log

### 2026-11-16 — done

**Deleted from the app:** the sync `rag_service.retrieve_context`,
`load_context_by_ids`, `generate_rag_answer`; `embedding_service`
`create_embeddings`, `_request_embeddings`, `embed_query`,
`search_similar_questions`; `deepseek_service._request`,
`chat_completion`, `generate_answer`; `query_embedding_repository.get` /
`create` / `touch`; `embedding_repository.search_similar_embeddings`;
`question_repository.get_questions_by_ids`;
`question_concept_repository.get_concepts_for_questions`. `core/openai.py`
and `core/deepseek.py` now hold only `async_client`. Surviving async
functions whose docstrings said "As `<deleted>`" carry the originals'
wording; comments about statements "shared by both variants" were
reworded, since there is one variant now.

**Tests (no test deleted):** none of the 13 sync tests in
`test_rag_service.py` had an async twin - the async RAG functions were
covered only through `/ai/ask` - so all 13 now exercise the async
functions, arranging rows with `db` and committing first. Also moved:
three vector-search tests in `test_embedding_repository.py`, three in
`test_embedding_service.py` (the OpenAI-error test now fakes
`async_client`), and the two `get_concepts_for_questions` tests in
`test_question_concept_repository.py`. `conftest` helpers install stubs
on the async seam only; `test_seed.py` guards the one remaining OpenAI
request. The architecture test that pinned the two sync-client users
is now `test_no_sync_llm_client_exists`; a planted `from openai import
OpenAI` was confirmed to fail it, then removed. `docs/development.md`'s
test conventions name the async seams.

**Found while testing: a shared test-settings file.** A suite run aborted
with "Another test run is using this database". The other run belonged
to a session in the `oak` checkout, which was using - and rewriting with
`sed` - the test-settings file this work had created in a scratchpad
during [87]. The suite's advisory lock did its job and aborted the
second run rather than let them share a database. From this slice on,
this work uses its own settings file and database name
(`physics_ai_tutor_test_elm_s108`). Earlier results stay valid: every
reported run completed fully, and a clash aborts at once instead of
passing.

**Results:** 622 passed (same count; nothing deleted), `ruff check`,
`ruff format --check`, `mypy` clean. Frontend untouched.

## Rules (all [73] slices)

- Twins only while an unconverted caller needs the sync version; delete a
  sync function in the slice that removes its last caller.
- Tests that call converted code are async on `async_db`; arrange with
  `db` and commit. List `async_db` before `admin_client` ([87]).
- Reference production code: `git diff 260d7c2 9c42cfd -- <paths>` on
  `wip/73-async-remaining` (its twins are collapsed; adapt, do not copy).

## Definition of done

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] Log entry in this file; `status.md`, [67], [73] and [88] updated
