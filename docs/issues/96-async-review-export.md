---
title: "[96] Asynchronize the review dataset export"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: admin export. No behaviour change.

## Scope

- Route `GET /admin/reviews/export` (async generator, same NDJSON).
- `review_export_service` (outright); `cli/export_reviews.py` via
  `asyncio.run`.
- Delete the sync twin `review_metrics_repository.ai_reviews_by_question`
  that [87] left; this slice removes its last caller. Fold
  `_ai_reviews_select` and `_group_by_question` back into the async
  version if nothing else needs them.

## Acceptance criteria

- [x] Export lines byte-identical for the same rows (fixture); `test_review_export.py` green.

## Dependencies

- Blocked by: [87]
- Blocks: [97]

## Log

### 2026-11-15 — done

**Converted:** `GET /admin/reviews/export` is async;
`review_export_service.iter_export_rows` is an async generator and
`to_jsonl` takes a plain iterable; `cli/export_reviews.py` runs the
service through `asyncio.run` (same arguments, exit value and stderr
line). `question_review_repository.list_with_questions_since` converted
outright, which makes that repository fully async. No behaviour change;
the existing file-vs-database comparison test pins the bytes.

**Deleted:** the sync `review_metrics_repository.ai_reviews_by_question`
twin from [87]; this slice removed its last caller, and the shared
statement/grouping helpers were folded back into the async version.

**Left as is:** the sync `question_concept_repository
.get_concepts_for_questions` still has sync callers in
`ai_review_service` and `rag_service`; the export now uses the existing
async twin, and [97] removes those last sync callers.

**Results:** 614 passed, `ruff check`, `ruff format --check` and `mypy`
clean. Frontend untouched.

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
