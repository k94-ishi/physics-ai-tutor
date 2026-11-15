---
title: "[106] Prompt eval on the async reviewer; delete the sync reviewer (one ai_review_service)"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [97] and [73]

## Summary

Last slice of [97]: the prompt eval ([17]) grades through the async
reviewer, and the sync reviewer is deleted. No behaviour change.

## Scope

- `cli/eval_prompts.py` via `asyncio.run`: `grade_cases` awaits
  `async_generate_answer` and `async_grade_answer`, still **one case at
  a time** so the printed order and the baseline stay identical.
- Delete the sync `grade_answer`, `review_question`,
  `review_question_with_outcome` and `_build_context`; their remaining
  tests move to `async_review_question`.
- After this `ai_review_service` imports no sync `Session`.
- `ai_review_repository.create`, `get_latest_for_question` and
  `list_for_question` (sync) are then used only by tests, to arrange
  rows; move them into a test helper or keep them for [88] to decide
  (noted by [105]).

## Acceptance criteria

- [ ] `eval_prompts --dry-run` works; `test_eval_prompts.py` green;
      committed baseline unchanged.
- [ ] Prompt texts and versions untouched (no `prompt_library.yaml`
      change, so no fingerprint bump).

## Out of scope

- The sync halves of `rag_service`, `deepseek_service` and
  `embedding_service` lose their last production caller here; [88]
  deletes them with the sync clients.

## Dependencies

- Blocked by: [105]
- Blocks: [88]

## Rules (all [73] slices)

- Twins only while an unconverted caller needs the sync version; delete a
  sync function in the slice that removes its last caller.
- Tests that call converted code are async on `async_db`; arrange with
  `db` and commit.
- Reference production code: `git diff 260d7c2 9c42cfd -- <paths>` on
  `wip/73-async-remaining` (its twins are collapsed; adapt, do not copy).

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Log entry in this file; `status.md`, [67], [73] and [97] updated
