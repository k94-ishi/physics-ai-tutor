---
title: "[93] Asynchronize create and update (prepare/apply)"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: admin create and edit. No behaviour change.

## Scope

- Routes `POST /questions`, `PUT /questions/{id}`.
- `create_question`, `update_question`: translate and embed with no
  session, then one short transaction; both leave the [82] allowlist.
- Keep the legacy `question=/answer=/language=` form; pin it with a test.

## Acceptance criteria

- [x] Create/update tests green; both body shapes accepted; rollback-on-embedding-failure tests still pass.

## Dependencies

- Blocked by: [86]
- Blocks: [94]

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

608 tests pass (607 + 1 new probe); ruff and mypy clean; frontend
untouched. 5 production files, 5 test files.

**The [82] shape for both.**

- *Create*: a short read checks for duplicates; then, with no
  transaction open, the new row is built as an unsaved draft, its texts
  are embedded, its concepts extracted and planned (when APPROVED), and
  the missing language translated; one short transaction inserts the
  row with its embeddings, translations, concepts and levels.
- *Update*: a short read; the edit is embedded and machine counterparts
  re-translated on a detached draft; one short transaction writes the
  levels, texts, embeddings and translations.
- Failure rules unchanged: an embedding failure writes nothing; a failed
  extraction or translation is skipped.

`create_question` and `update_question` left the [82] allowlist; only
`import_questions_from_jsonl` remains ([94]). A runtime probe checks
embedding, extraction and translation during a create.

**Shared with [85].** `draft_of` and `async_prepare_refresh` moved into
`question_translation_service`; review and update use the same two
functions. `question_repository.build_question` builds an unsaved row.
The "translation skipped" log lines use `%s`, since a draft has no id
yet.

**Still sync, on purpose:** `embed_language`, `translate_missing`,
`refresh_machine_translations` and `attach_concepts_best_effort` are
used by import and the seed until [94]/[95].

**Tests.** The module's `_create` helper is now a sync bridge to the
async service (as `create_user` is), with `_acreate` / `_acreate_row`
for async tests; the update tests are async. The two body shapes were
already pinned through the API (`test_language.py`: legacy ja/en,
explicit both-languages, half pair). Three strict-language tests broke
only the sync translator to make untranslated rows; they now use
`patch_translate_qa` so both seams fail. A search for other sync-only
seam patches found three, all on code that is still sync.
