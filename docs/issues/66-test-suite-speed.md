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

## Log

### 2026-11-11 - done: 5 min 56 s -> 38 s

| Run | Suite | Seed setup | Machine load |
| --- | --- | --- | --- |
| before [58] | 356 s | 256 s (7 seeds) | - |
| after [58] | 121-158 s | 17-147 s | 3-6 |
| after [66] | **38 s** (twice) | 10-12 s | 9 |

Findings, in the order of the scope:

1. **The in-suite seed slowdown was machine load, not the suite.** Bisecting
   the files that run before `test_seed.py` never reproduced it (17-18 s
   in every half), and a quiet full run gave 17.5 s. The seed made ~17,000
   tiny round trips, so it was the part most sensitive to a busy machine
   (7 sessions, a shared `postgres-test` container).
2. **Seed round trips: 16,632 -> 3,590 statements.** Concept attachment
   looked up each word, loaded its terms, checked each link and updated
   each new concept's name separately (~7.6 statements per tag). Now one
   lookup per question for all its words (`senses_by_words`), one link
   check (`link_many`), and a new concept inserted with its words. Same
   matching rules; this is the production extraction path too.
3. **Per-test initialization was 127 of 157 s** (setup 92 s, teardown
   35 s; the test bodies only 30 s), confirming the owner's point. Two
   shared costs, fixed for every test:
   - table reset: `TRUNCATE ... RESTART IDENTITY CASCADE` twice per test
     (~40 ms each) -> one `DELETE` batch + sequence restart before the
     test only (~2 ms). Same end state (ids still start at 1).
   - password hashing: Argon2 at production cost (~50 ms per hash, ~110 ms
     per admin/user login, 160 tests) -> minimal cost in tests;
     `test_security.py` pins the production parameters and shows stored
     production hashes still verify.
4. Rollback-per-test isolation and `pytest-xdist` were **not** needed.
   Rollback isolation would break the tests whose background tasks open
   their own session (they must see committed rows); xdist adds a database
   per worker for little gain at 38 s.
5. CI prints `--durations=10`.

On the owner's suggestion of grouping tests into shared-setup classes:
measured first. With the shared costs fixed, the remaining per-test setup
is a few milliseconds, so grouping would trade test independence (order,
leaked state) for almost no time. The one place where it pays - an
expensive, read-only setup - already uses it (`test_seed.py`, one seed per
module). The rule is written in docs/development.md.
