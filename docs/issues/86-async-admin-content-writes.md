---
title: "[86] Asynchronize admin content writes: create, update, delete, import; the seed and backfill CLIs follow"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], slice 5 of [73]

## Summary

Convert the admin routes that create, edit, delete and import questions,
and with them the last sync callers of the translation and embedding
services: the seed and three CLIs. After this slice
`question_translation_service` has one implementation per function.

## Motivation

Create, update and import each translate and embed inside their
transaction (three of the four [82] allowlist entries), and import is
the slowest admin action there is. Converting them finishes the write
side of the question domain and lets the sync half of the translation
service be deleted, which is where most of the remaining duplication
lives.

## Scope

- Routes in `api/v1/admin_questions.py`: `POST /questions`, `PUT
  /questions/{id}`, `DELETE /questions/{id}`, `POST
  /questions/bulk-delete`, `POST /questions/import`.
- `question_write_service`: `create_question`, `update_question`,
  `delete_question`, `bulk_delete_questions`,
  `import_questions_from_jsonl`, `_check_duplicates`,
  `_find_duplicate_texts`; `async_save_ai_question` from [70] keeps its
  name until [88].
- `create_question` and `update_question`: prepare (translate and embed,
  no session) then apply (one short transaction) - their [82] allowlist
  entries go. `import_questions_from_jsonl`: if [76] has landed, its
  collect-texts, batch-embed, bulk-write shape is already prepare/apply
  and the entry goes too; if not, convert it keeping its transaction,
  rename the allowlist entry to the async name, and leave the removal
  to [76]. **Doing [76] first is the recommended order.**
- `question_translation_service`: delete the sync half
  (`embed_language`, `translate_into`, `translate_missing`,
  `prepare_translation`, `apply_translation`,
  `translate_missing_languages`, `refresh_machine_translations`) once
  these routes, the seed and the CLIs use the async ones.
- `concept_service`: the remaining sync matching/attach functions used
  by create and by the seed; `embedding_service.create_embeddings` sync
  twin and its `_preloaded` shortcut - the seed must keep serving
  vectors from `seed_embeddings.jsonl.gz` through the async path with
  zero OpenAI calls.
- Scripts whose callees go async here: `database/seed.py`,
  `cli/backfill_levels.py`, `cli/split_merged_concepts.py`,
  `cli/translate_missing.py` - each becomes `asyncio.run(main())` on
  `AsyncSessionLocal`, behaviour unchanged (`test_cli.py`,
  `test_seed.py`).
- The legacy single-language create form
  (`question=`/`answer=`/`language=`) stays accepted: the [73] attempt
  found the async `create_question` had dropped it. Add a test that
  pins it.

## Acceptance criteria

- [ ] The five routes are `async def` on `get_async_db`.
- [ ] `question_translation_service` has no sync/async twin pairs.
- [ ] Import stays all-or-nothing on duplicate text; a bad line still
      rejects the whole file with per-line errors.
- [ ] The offline seed still makes zero OpenAI and zero DeepSeek calls
      (`test_seed.py` guarantees kept).
- [ ] The [82] allowlist is empty, or holds only
      `import_questions_from_jsonl` if [76] has not landed.
- [ ] Both create body shapes accepted, pinned by tests.

## Out of scope

- Batching the embedding calls themselves ([76]).
- Review and bulk-review ([85]); stats, exports and runs ([87]).
- Deleting the sync engine and the remaining twins elsewhere ([88]).

## Technical notes

Reference on `wip/73-async-remaining`:
`git diff 260d7c2 9c42cfd -- backend/physics_ai_tutor/services/{question_write,question_translation,embedding}_service.py backend/physics_ai_tutor/database/seed.py backend/physics_ai_tutor/cli/{backfill_levels,split_merged_concepts,translate_missing}.py`.
Since this slice is where the translation twins actually die, the WIP
versions of those files are close to the target.

Test churn estimate: the largest of the slices, about 60 tests - the
write half of `test_question_service.py` (~20),
`test_question_concept_repository.py` 8, `test_embedding_repository.py`
6, `test_embedding_service.py` 3, `test_difficulty_levels.py` 4,
`test_cli.py` 9, `test_seed.py` 6, plus the import-shape tests in
`test_language.py`. If it grows past that, split along "create, update,
delete" and "import plus scripts"; the seam between them is
`question_translation_service`, whose sync half then survives one more
slice.

A `def` to `async def` pass must count only the awaits of the function
itself, not of nested functions - the [73] attempt turned the
`conftest.create_user` bridge async by walking the whole subtree.

## Dependencies

- Blocked by: [85] (shares the translation and extraction seams).
  Preferably also [76].
- Blocks: [88].

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Frontend untouched; CI green
- [ ] `docs/development.md`: the CLI examples still correct (commands
      do not change); the [82] allowlist sentence updated
