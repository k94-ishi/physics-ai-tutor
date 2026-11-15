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

- [x] `eval_prompts --dry-run` works; `test_eval_prompts.py` green;
      committed baseline unchanged.
- [x] Prompt texts and versions untouched (no `prompt_library.yaml`
      change, so no fingerprint bump).

## Out of scope

- The sync halves of `rag_service`, `deepseek_service` and
  `embedding_service` lose their last production caller here; [88]
  deletes them with the sync clients.

## Dependencies

- Blocked by: [105]
- Blocks: [88]

## Log

### 2026-11-16 — done; closes [97]

**Converted:** `eval_prompts.grade_cases` is async and awaits
`async_generate_answer` / `async_grade_answer`, still one case at a time
so the printed order and the baseline cannot depend on scheduling;
`main` wraps it in `asyncio.run`. Arguments and output unchanged;
`--dry-run` verified for real: 68 cases, no API call, exit 0.

**Deleted:** the sync `grade_answer`, `review_question`,
`review_question_with_outcome` and `_build_context`. `ai_review_service`
now has one implementation of everything and imports no sync `Session`
or `transaction`.

**The repository trio:** `create`, `get_latest_for_question` and
`list_for_question` had no production caller left ([105]'s note), so per
[97]'s "no sync function in `ai_review_repository`" they went too. Sync
tests arrange rows through a new `tests/conftest.create_ai_review`
helper (same `_new_review` mapping the async write uses, flush not
commit); `test_ai_review_schema.py` reads back with two local query
helpers that keep the deleted readers' newest-first order. Seven test
files touched; `test_review_workflow.py` had an eighth `create` call the
first sweep missed - the suite caught it.

**Eval tests:** stubs stay plain sync functions; a module-local
`_patch_grade` installs them on the async seam, following the
`patch_generation` convention.

**Noticed, pre-existing:** there is no committed
`baseline-v5-r5.json` - the rubric became r5 in [51] and no baseline was
saved since (the newest is v5-r4). `--dry-run` reports it missing, and a
real eval would warn-and-pass rather than gate. Owner may want a
baseline run once prompts next change; nothing in this slice altered
prompts or baselines.

**Results:** 622 passed, `ruff check`, `ruff format --check`, `mypy`
clean. Frontend untouched.

## Rules (all [73] slices)

- Twins only while an unconverted caller needs the sync version; delete a
  sync function in the slice that removes its last caller.
- Tests that call converted code are async on `async_db`; arrange with
  `db` and commit.
- Reference production code: `git diff 260d7c2 9c42cfd -- <paths>` on
  `wip/73-async-remaining` (its twins are collapsed; adapt, do not copy).

## Definition of done

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] Log entry in this file; `status.md`, [67], [73] and [97] updated
