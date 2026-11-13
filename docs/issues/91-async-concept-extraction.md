---
title: "[91] Asynchronize concept extraction and the re-extract route"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: concept extraction seam. No behaviour change.

## Scope

- Route `POST /questions/concepts/extract`.
- `question_write_service.reextract_concepts_for_questions`,
  `extract_concepts_best_effort`, `attach_concepts_best_effort` and the
  extraction/matching path of `concept_service` (async twins; the seed
  and create still use sync until [93]/[95]).
- Left over from [90]: `concept_term_repository.senses_by_words`, the sync
  `get_many`, the sync `concept_sense_service.add_term`, and the dead
  `senses_with_any_term`.
- Prepare (LLM call, no session) then apply (short transaction); remove
  `reextract_concepts_for_questions` from the [82] allowlist.

## Acceptance criteria

- [ ] Re-extract tests green; a runtime probe shows no open transaction during extraction.

## Dependencies

- Blocked by: [90]
- Blocks: [85]

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
