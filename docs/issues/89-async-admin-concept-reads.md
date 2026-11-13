---
title: "[89] Asynchronize the admin tag editor reads: list and detail"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: admin tag list and detail. No behaviour change.

## Scope

- Routes `GET /admin/concepts`, `GET /admin/concepts/{id}`.
- `concept_sense_service.list_for_admin`, `detail_for_admin`, `_admin_item`.
- Remaining read twins in `concept_term_repository`
  (`admin_concept_ids`, `shared_word_partners`, `linked_questions`).

## Acceptance criteria

- [ ] `test_admin_list_filters_shared_words` and the admin-auth test green; `review`/`shared` filters return the same rows.

## Dependencies

- Blocked by: [84]
- Blocks: [90]

## Rules (all [73] slices)

- Twins only while an unconverted caller needs the sync version; delete a
  sync function in the slice that removes its last caller.
- Tests that call converted code are async on `async_db`; arrange with
  `db` and commit. Frontend untouched.
- Reference production code: `git diff 260d7c2 9c42cfd -- <paths>` on
  `wip/73-async-remaining` (its twins are collapsed; adapt, do not copy).

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Log entry in this file; `status.md`, [67] and [73] updated
