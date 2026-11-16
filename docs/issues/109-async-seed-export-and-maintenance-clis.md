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

- [x] No module outside `database/` imports `SessionLocal`; export files
      byte-identical (the round-trip tests).

## Dependencies

- Blocked by: [108]
- Blocks: [110]

## Log

### 2026-11-16 — done

**Converted:** `export_seed.build_entries` and
`export_seed_embeddings.collect` are async (`select()` in place of
`db.query`), and each `main` runs them through `asyncio.run`.
`init_db` runs `Base.metadata.create_all` through the async engine's
`run_sync`. `split_merged_concepts.find_suspect_links` and
`backfill_levels.unrated_question_ids` are async, and each command now
runs in one event loop. `SessionLocal` is now imported only inside
`database/`, which [110] deletes.

**A connection held across DeepSeek, removed ([82]).** Both maintenance
commands used to keep a sync session open while the async re-extraction
called DeepSeek, so one connection sat idle for the whole AI run. Each
read now happens in its own short session that closes before the AI
calls start (`_suspects`, `_unrated`). The off-peak check in
`backfill_levels` still runs before anything touches the database.

**Lazy loading checked:** the exports and the suspect check read
`Concept.terms`, which loads eagerly (`lazy="selectin"`), so no
implicit IO happens on the async session.

**Tests:** the two export round-trip tests in `test_seed.py` are async
and open an explicit `AsyncSession` - not `async_db`, which would empty
the module's seeded tables. `test_difficulty_levels.py` and the split
test in `test_concept_senses.py` no longer bind a sync factory; the
split test's final "nothing suspect left" check uses the command's own
`--dry-run` output instead of calling the function directly.

**Real entry points run:** `init_db`, both exports (output to a
scratchpad) and `split_merged_concepts --dry-run` ran against this
work's own test database through their real `asyncio.run` and session
setup; all exited 0 and left no files in the repo.

**Docs:** `docs/development.md`'s layers section said background tasks
use `background_session()` and CLIs keep `SessionLocal`; both have been
untrue since [72]/[109] and are corrected.

**Results:** 622 passed, `ruff check`, `ruff format --check`, `mypy`
clean. Frontend untouched.

## Rules (all [73] slices)

- Twins only while an unconverted caller needs the sync version; delete a
  sync function in the slice that removes its last caller.
- Tests that call converted code are async on `async_db`; arrange with
  `db` and commit. List `async_db` before `admin_client` ([87]).
- Reference production code: `git diff 260d7c2 9c42cfd -- <paths>` on
  `wip/73-async-remaining` (its twins are collapsed; adapt, do not copy).

## Definition of done

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] Log entry in this file; `status.md`, [67], [73] and [88] updated
