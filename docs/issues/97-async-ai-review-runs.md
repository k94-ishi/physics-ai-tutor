---
title: "[97] Asynchronize AI review runs; one ai_review_service"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: AI review runs. No behaviour change.

## Scope

- Routes `POST/GET /admin/ai-review/runs`, `GET .../runs/{id}`,
  `GET .../pending-count`.
- Collapse the twin pairs in `ai_review_service`; `ai_review_repository`
  outright; `cli/review_pending.py` and `cli/eval_prompts.py` via
  `asyncio.run` (nightly workflow unchanged).

## Acceptance criteria

- [ ] 409/429/timeout semantics unchanged; `test_ai_review_service.py` green; `eval_prompts --dry-run` works.

## Dependencies

- Blocked by: [96]
- Blocks: [88]

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
