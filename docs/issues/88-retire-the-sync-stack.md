---
title: "[88] Delete the sync engine, sync LLM clients and remaining sync twins (umbrella for [107]-[112])"
labels: [backend, async, refactor, epic]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

Deletions: once every caller is async, the sync engine, the sync LLM
clients and every remaining sync function leave the app. No behaviour
change. Tests keep a test-only sync session in conftest.

**Split 2026-11-16** into six slices, each its own commit with the suite
green. This issue stays open until all six are closed.

## Scope: the slices

| # | Issue | What goes | Status |
| --- | --- | --- | --- |
| 1 | [107] | Sync rate limiter; dead sync repository functions | done 2026-11-16 |
| 2 | [108] | Sync RAG path; sync OpenAI and DeepSeek clients | done 2026-11-16 |
| 3 | [109] | `export_seed`, `export_seed_embeddings`, `init_db`, `split_merged_concepts`, `backfill_levels` onto the async engine | done 2026-11-16 |
| 4 | [110] | Sync `engine`, `SessionLocal`, `get_db`, `background_session`, `transaction()` | open |
| 5 | [111] | Test-only sync helpers in `question_repository` | open |
| 6 | [112] | Test-only sync helpers in the concept and embedding repositories | open |

Chain: [107]→[108]→[109]→[110]→[111]→[112]→[98].

## Acceptance criteria (ticked when [112] closes)

- [ ] `rg "SessionLocal|get_db"` matches only `database/`, `alembic/`, `tests/`.
- [ ] No sync LLM client; no app module takes a sync `Session`.

## Dependencies

- Blocked by: [95], [97] (both done 2026-11-16)
- Blocks: [98]

## Log

### 2026-11-16 — split into [107]-[112]

Measured against the code (HEAD 0dc6a2b) with an AST scan of every
function that takes a sync `Session`, counting only module-qualified
callers:

- **No production path uses the sync stack any more.** Every remaining
  sync function is dead (4) or reached only from tests (~20 entry
  points), apart from five CLIs that still open `SessionLocal`.
- The test churn is about 85 tests: sync RAG/LLM path ~19, rate limiter
  5, CLIs ~6, and **57** for sync repository helpers that tests use to
  arrange rows. That is roughly eight times the owner's ten-test slice.
- The helpers (slices 5-6) must go before [98]: renaming
  `async_create_question` to `create_question` would collide with the
  sync function of the same name.
- The engine itself (slice 4) needs only slices 1-3: the test-only
  helpers take a session as a parameter and never import the engine.

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

- [ ] [107]-[112] closed
- [ ] Log entry in this file; `status.md`, [67] and [73] updated
