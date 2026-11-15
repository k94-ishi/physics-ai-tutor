---
title: "[109] Seed export, init_db and the maintenance CLIs on the async engine"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [88] and [73]

## Summary

Third slice of [88]: the last production users of `SessionLocal`. No
behaviour change.

## Scope

- `cli/export_seed.py`, `cli/export_seed_embeddings.py` and
  `database/init_db.py` via `asyncio.run` (named in [88] from the start).
- `cli/split_merged_concepts.py` (`find_suspect_links`) and
  `cli/backfill_levels.py` (`unrated_question_ids`): their LLM halves are
  async since [91]; the reads around them still open a sync session.
- Tests: `test_seed.py` export round trips, the split CLI tests in
  `test_concept_senses.py`, `test_difficulty_levels.py`.

## Acceptance criteria

- [ ] No module outside `database/` imports `SessionLocal`; export files
      byte-identical (the round-trip tests).

## Dependencies

- Blocked by: [108]
- Blocks: [110]

## Rules (all [73] slices)

- Twins only while an unconverted caller needs the sync version; delete a
  sync function in the slice that removes its last caller.
- Tests that call converted code are async on `async_db`; arrange with
  `db` and commit. List `async_db` before `admin_client` ([87]).
- Reference production code: `git diff 260d7c2 9c42cfd -- <paths>` on
  `wip/73-async-remaining` (its twins are collapsed; adapt, do not copy).

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Log entry in this file; `status.md`, [67], [73] and [88] updated
