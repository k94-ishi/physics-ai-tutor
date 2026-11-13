---
title: "[84] Asynchronize the public tag search (`GET /concepts`)"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: student tag search only. No behaviour change.

## Scope

- Route `GET /concepts` in `api/v1/concepts.py`.
- `concept_sense_service.search` (and the pure `label`, `_rank`).
- `concept_term_repository.search_terms`, `most_linked`, `question_counts`,
  `get_many`: async twins (the admin editor still uses the sync ones).

## Acceptance criteria

- [ ] Search tests in `test_concept_senses.py` (5) stay green; strict rule kept: students see only senses with APPROVED questions and a label in `lang`.

## Dependencies

- Blocked by: [83]
- Blocks: [89]

## Log

### 2026-11-13 — re-scoped smaller

Owner found [83] (22 files, 35 tests) too big. The earlier, wider version of this issue was split; see [73]'s table.

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
