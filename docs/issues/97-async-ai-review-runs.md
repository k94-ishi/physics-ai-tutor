---
title: "[97] Asynchronize AI review runs; one ai_review_service (umbrella for [103]-[106])"
labels: [backend, async, refactor, epic]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

AI review runs, the nightly CLI and the prompt eval move to the async
stack, and `ai_review_service` ends with one implementation of each
function. No behaviour change except where [105] says so.

**Split 2026-11-15** into four slices, each its own commit with the
suite green. This issue stays open until all four are closed.

## Scope: the slices

| # | Issue | What converts | Status |
| --- | --- | --- | --- |
| 1 | [103] | Run reads: list, detail, pending count | done 2026-11-15 |
| 2 | [104] | Starting a run (`POST /admin/ai-review/runs`): 409 / 429 / reaping | done 2026-11-16 |
| 3 | [105] | Nightly `review_pending` CLI on the async executor; sync run code deleted | done 2026-11-16 |
| 4 | [106] | Prompt eval on the async reviewer; sync reviewer deleted | open |

Chain: [103]→[104]→[105]→[106]→[88].

## Acceptance criteria (ticked when [106] closes)

- [ ] 409/429/timeout semantics unchanged; `test_ai_review_service.py`
      green; `eval_prompts --dry-run` works.
- [ ] No sync function left in `ai_review_service` or
      `ai_review_repository`; no route in `api/v1/admin.py` uses `get_db`.

## Dependencies

- Blocked by: [96]
- Blocks: [88]

## Log

### 2026-11-15 — split into [103]-[106]

The owner found the single issue too big. Measured against the code
(HEAD 96bc458):

- `ai_review_service.py` (823 lines) holds sync and async halves of the
  reviewer, the run lifecycle and the counters; about 15 of the 33 tests
  in `test_ai_review_service.py` call the sync `start_run` /
  `execute_run` / `review_question` directly, plus 6 CLI tests and 8
  eval tests. Converting all of that at once is the [83] shape again.
- The split follows the callers: reads first (no test churn), then the
  start route, then the CLI (which removes the last caller of the sync
  executor), then the eval (which removes the last caller of the sync
  grader).
- **Found while splitting:** the nightly CLI still runs the *sync*
  executor, one question at a time, while admin-started runs use the
  concurrent async one from [72]. Moving the CLI over is therefore a
  visible change (faster nightly runs; a crashing question fails one
  item, not the whole run). [105] records it for the owner to confirm.
- **Also found:** the sync `execute_run_in_background` had no caller;
  [103] deleted it.

## Rules (all [73] slices)

- Twins only while an unconverted caller needs the sync version; delete a
  sync function in the slice that removes its last caller.
- Tests that call converted code are async on `async_db`; arrange with
  `db` and commit. Frontend untouched.
- Reference production code: `git diff 260d7c2 9c42cfd -- <paths>` on
  `wip/73-async-remaining` (its twins are collapsed; adapt, do not copy).

## Definition of done

- [ ] [103]-[106] closed
- [ ] Log entry in this file; `status.md`, [67] and [73] updated
