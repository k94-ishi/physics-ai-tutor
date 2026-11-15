---
title: "[112] Test-only sync helpers in the concept and embedding repositories move out of the app"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [88] and [73]

## Summary

Last slice of [88]: the remaining sync repository functions, all called
only by tests. No behaviour change.

## Scope

- `concept_repository.create`, `get_by_name`, `list_all`;
  `embedding_repository.create_embedding`, `create_embeddings`,
  `delete_by_question_id`; `question_concept_repository.link`,
  `get_concepts_for_question`, `get_concept_ids_for_question`,
  `delete_by_question_id`.
- Same rule as [111]: repository tests move to the async functions;
  arrangement goes through sync helpers in `tests/`.
- ~27 tests across `test_question_concept_repository.py`,
  `test_embedding_repository.py`, `test_concept_service.py`,
  `test_recommendation_service.py` and others.

## Acceptance criteria

- [ ] No repository imports `sqlalchemy.orm.Session`; [88] can close.

## Dependencies

- Blocked by: [111]
- Blocks: [98]

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
