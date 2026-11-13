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

- [x] `test_admin_list_filters_shared_words` and the admin-auth test green; `review`/`shared` filters return the same rows.

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

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] Log entry in this file; `status.md`, [67] and [73] updated

## Log

### 2026-11-13 — done

602 tests pass (601 + 1 new); ruff and mypy clean; frontend untouched.

- `GET /admin/concepts` and `GET /admin/concepts/{id}` are async.
- `list_for_admin` and `admin_concept_ids` had only the list route as a
  caller, so they are async outright.
- `detail_for_admin`, `shared_word_partners` and `linked_questions` got
  async twins, because the six editor write routes ([90]) still return
  the sync detail. Each pair runs one shared statement
  (`_partners_select`, `_linked_questions_select`), and the pure
  `_admin_item` lost its unused `db` argument.
- New test: the detail lists linked questions, word-sharing partners and
  the count, and an unknown id is a 404 (the detail had no direct test
  before; the split test only touched it in passing).
