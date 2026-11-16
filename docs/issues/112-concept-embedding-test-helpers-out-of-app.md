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

- [x] No repository imports `sqlalchemy.orm.Session`; [88] can close.

## Dependencies

- Blocked by: [111]
- Blocks: [98]

## Log

### 2026-11-16 — done; closes [88]

**Ten sync functions, the same three kinds as [111]:**

- **Arrangement helpers** with no production caller:
  `concept_repository.create` and `question_concept_repository.link`
  (the app creates senses and links through `concept_sense_service` and
  `async_link_many`), and `embedding_repository.create_embedding` as a
  setup tool. They became `conftest.create_concept`, `link_concept` and
  `create_embedding`, built on the same `build` / `_new_embedding`
  mappings the app uses. A fourth helper, `concepts_for_question`,
  replaces the sync reader that tests used to inspect results (12 sites
  in `test_question_service.py`).
- **Readers and deletes with async twins**
  (`get_concepts_for_question`, `get_concept_ids_for_question`, both
  `delete_by_question_id`, `create_embedding`'s own tests): their
  repository tests now exercise the twins. The two `link` tests now test
  `async_link_many`, which is what production calls; the idempotency
  test also covers a repeated id inside one call.
  `test_async_concept_readers_match_the_sync_ones` compared against the
  sync readers; it now asserts the expected values directly.
- **Dead code:** the bulk `embedding_repository.create_embeddings` had
  no caller; deleted with its one test. `concept_repository.get_by_name`
  and `list_all` were test-only readers; six call sites became direct
  queries.

**Order of work:** tests were moved off the sync functions first (suite
green with them still present), then the functions were deleted and the
suite re-run, so a failure would have pointed at one step.

**[88]'s criteria verified:** no `SessionLocal` / `get_db` outside
`database/`, `alembic/`, `tests/`; no sync `OpenAI` client; an AST scan
finds no app function that takes a sync `Session` and no app import of
`Session` or `sessionmaker`.

**Shared test database, again:** a run aborted on the suite's lock: an
`oak` session was now loading the settings file created in [108]. That
run was left alone. Checks from here use a script that exports the
settings in-process and picks a random database name per run, so no
file or name can be shared. Superseded by [113]: the suite now starts
its own database and needs no settings at all.

**Results:** 614 passed (615 minus the dead bulk-create test), `ruff
check`, `ruff format --check`, `mypy` clean. Frontend untouched.

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
