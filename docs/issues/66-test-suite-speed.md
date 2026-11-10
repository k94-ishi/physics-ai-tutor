---
title: "[66] Test suite speed: backend 4.5 min -> under 2 min"
labels: [testing, performance, refactor]
milestone: M1 Student value
priority: P1
---

**Priority:** P1  **Milestone:** M1 — Student value  **Track:** [57]

## Summary

The backend suite took 5 min 56 s on 2026-11-10 (520 tests); [58] cut it
to 4 min 27 s by seeding once per module instead of seven times. Slow
local runs make every refactor step in [57] expensive, so this goes early.

## Measurements (2026-11-10)

| What | Time |
| --- | --- |
| 7 seed tests before [58] | 256 s of 356 s |
| the one module seed after [58], **inside the suite** | 147 s |
| the same seed, **alone** | 20-27 s |
| the other ~513 tests | ~100 s (~0.2 s each) |
| frontend vitest (166 tests) | ~25 s - fine |

Profile of the seed alone: ~17,000 DB round trips (~117 per question),
10.5 s of 27 s spent waiting on the connection - an N+1 pattern in
concept attachment (`attach_concepts_to_question` looks up, flushes and
links each concept separately) and in per-row embedding inserts.

## Scope

1. **Find the in-suite slowdown** (147 s vs 25 s for identical work).
   Hypotheses to test, cheapest first: table/index bloat from ~500
   `TRUNCATE ... RESTART IDENTITY CASCADE` runs; autovacuum or the
   statistics going stale; another worktree's pytest sharing the
   `postgres-test` container; SQLAlchemy identity-map growth in a
   long-lived session.
2. **Cut the seed's round trips**: batch term lookups for all concepts of
   a question, bulk-insert embeddings and links, `selectin`-load terms
   once. Benefits production imports too.
3. **Cheaper isolation per test**: wrap each test in a transaction that
   is rolled back (SAVEPOINT pattern) instead of truncating every table
   twice; keep TRUNCATE only for tests that need a committed state
   (background tasks with their own session).
4. **Parallelism** (optional): `pytest-xdist` with one database per
   worker (the per-checkout database naming already exists).
5. Record the time in CI's job summary so regressions are visible.

## Acceptance criteria

- [ ] Backend suite under 2 minutes locally, the seed under 15 s inside it.
- [ ] No test weakened; the offline-seed guarantees stay tested.

## Dependencies

- Blocked by: [58] (done). Do before [59] so the refactor loop is fast.
