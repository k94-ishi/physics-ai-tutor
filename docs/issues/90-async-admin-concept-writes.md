---
title: "[90] Asynchronize the admin tag editor writes: gloss, words, merge, split"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: admin tag edits. No behaviour change.

## Scope

- Routes `PATCH /admin/concepts/{id}`, `POST .../terms`,
  `PATCH|DELETE .../terms/{term_id}`, `POST .../merge`, `POST .../split`.
- The write functions of `concept_sense_service`.
- `concept_term_repository` becomes async only (no sync caller left).

## Acceptance criteria

- [x] 409 on duplicate word, label takeover on delete, merge and split behave as before (4 tests).

## Dependencies

- Blocked by: [89]
- Blocks: [91]

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

### 2026-11-13 — done

602 tests pass; ruff and mypy clean; frontend untouched. 3 production
files, 1 test file.

- The six editor routes (gloss, add/edit/delete word, merge, split) and
  their use cases are async on `async_transaction`.
- `merge`, `split`, `set_preferred`, `delete_term`, `edit_term` had no
  caller outside the editor, so they are async outright. The raw
  `db.query` calls in `merge` and `split` moved into the repository
  (`linked_question_ids`, `links_of`, `move_links`).
- The [89] twins lost their last sync caller and are gone:
  `detail_for_admin`, `question_counts`, `shared_word_partners`,
  `linked_questions` now exist once, async, under the plain name.
- `split` builds the new sense with `terms=[]`: otherwise the duplicate
  check reads an unloaded collection, which an AsyncSession refuses.
- **Not async-only yet**, unlike this issue's scope said:
  `concept_term_repository.senses_by_words` and the sync `get_many`
  (and the sync `add_term` in the service) are still used by concept
  extraction; they go in [91]. `senses_with_any_term` has no caller at
  all; left for [91] to delete with its neighbours.
- One test changed, not the behaviour: `test_merge_moves_questions_and_words`
  read `a.id` after `expire_all()`. The route used to share the test's
  session, so the deletion was visible there; it now has its own
  session, so the id is captured before the request.
