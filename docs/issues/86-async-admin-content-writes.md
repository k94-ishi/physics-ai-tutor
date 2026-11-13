---
title: "[86] Asynchronize delete and bulk delete"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: admin deletes (no LLM). No behaviour change.

## Scope

- Routes `DELETE /questions/{id}`, `POST /questions/bulk-delete`.
- `question_write_service.delete_question`, `bulk_delete_questions`;
  async `question_repository.delete`.

## Acceptance criteria

- [ ] Cascade to embeddings, links and reviews unchanged; delete tests green.

## Dependencies

- Blocked by: [92]
- Blocks: [93]

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
