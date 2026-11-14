---
title: "[95] Seed and translation CLIs on the async services; delete the sync translation half"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: scripts. No behaviour change.

## Scope

- `database/seed.py`, `cli/backfill_levels.py`,
  `cli/split_merged_concepts.py`, `cli/translate_missing.py` use
  `asyncio.run` on `AsyncSessionLocal`.
- Delete the sync half of `question_translation_service` and the
  remaining sync `concept_service` functions.

- `tests/test_seed.py` forbids AI calls by patching only the **sync**
  seams (`extract_concept_names`, `translate_qa`). When the seed moves
  to the async services, forbid the async seams too, or the "zero AI
  calls" guarantee passes vacuously (found in [93]).

- Done early in [94]: the seed's import step is async and its test
  forbids both sync and async AI seams. Left here: the stored-tags step
  (`apply_seed_extras`, sync `attach_concepts_to_question`,
  `extract_concepts_best_effort`), the three CLIs, the sync
  `translate_missing_languages`.

## Acceptance criteria

- [ ] Offline seed still makes zero OpenAI/DeepSeek calls (`test_seed.py`); `test_cli.py` green.

## Dependencies

- Blocked by: [94]
- Blocks: [87]

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
