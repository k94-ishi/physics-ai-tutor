---
title: "[99] Async end state: architecture test, docs, connection budget"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: closing the migration. No behaviour change.

## Scope

- `test_architecture.py` forbids sync `Session` and `sessionmaker`
  outside `database/`, `alembic/`, `tests/`; obsolete checks removed
  (at least `test_async_code_never_uses_the_sync_transaction_helper`,
  whose helper [110] deleted).
- `docs/development.md`: drop the two-stack section; one pool per worker.
- Re-measure connections per worker ([75] table) on a quiet machine.

## Acceptance criteria

- [x] [73]'s acceptance criteria all ticked; [73] closed.

## Dependencies

- Blocked by: [98] (done 2026-11-17)
- Blocks: closes [73]

## Log

### 2026-11-17 — done; closes [73]

**Architecture test.** New `test_the_app_has_no_sync_database_access`:
no `sqlalchemy.orm.Session`, `sessionmaker`, `scoped_session` or
`create_engine` anywhere in the package, `database/` included - stricter
than the scope's "outside `database/`", because since [110] `database/`
has none either. Alembic and tests are outside the package. Checked by
planting `from sqlalchemy.orm import Session` in a service: the test
failed naming the file; the probe was removed. Removed as obsolete:
`test_async_code_never_uses_the_sync_transaction_helper` (the helper is
gone; `with` on the async one fails at once anyway), the empty
`KNOWN_TRANSACTION_LLM_CALLERS` allowlist and its staleness test.

**The [82] tripwire had gone stale.** `LLM_CALLS` named three functions
that no longer exist and missed about 25 that reach a provider today -
the prepare halves of the prepare/apply split, `embed_many`,
`review_question`, `search_similar_questions` and others - so a
transaction around any of them would have passed. The list now holds
the provider seams plus every one-hop function; the rule still passes.

**Docs.** The two-stacks section of `docs/development.md` became "The
async stack": one table of where sessions, writes and engines live, and
the rules that still apply. The worker section has the new budget.

**Connection budget, re-measured** (same probe as [75]: 800 requests to
`/questions?size=50` at concurrency 32; 144 seeded questions):

| Workers | Worst case | Peak under load | Held when idle |
| --- | --- | --- | --- |
| 1 | 15 | 15 | 6 |
| 2 | 30 | 30 | 11 |
| 4 | 60 | 47 | 21 |

The idle figures match [75]'s 6 / 11 / 21. Pools filled to their
ceiling under load, so the budget is the worst case: against ~60 direct
Supabase connections, two workers are safe, three fit, four reach the
limit exactly (before [110], 120). [74] picks the final pool sizes.

**What went wrong on the way, so the numbers can be trusted:**

- The first two runs were invalid. `kill` reached the `uv run` wrapper,
  not the uvicorn inside it, so the 1-worker server kept port 18099; the
  2- and 4-worker servers failed to bind and the load went to the old
  server, whose database was gone (fast 500s looked like good latency).
  Fixed by starting the server from `.venv/bin` (real PID), a fresh
  port per run, a check that the listener is the server just started,
  "every response 200" and "server gone afterwards" checks. The stale
  server was mine and was stopped.
- `ENVIRONMENT=development` logs every SQL statement; the measurement
  uses `production`.
- A connection sampler via `docker exec` was too slow to see peaks;
  replaced by a 50 ms sampler on one connection.
- Another session ran its own benchmark at the same time (load average
  up to 12 on 8 cores); it was left alone. Connection counts do not
  depend on it; **latency does**, so no latency is recorded here.

**Found: [114].** `/questions?size=50` costs 143-1,380 ms sequentially on
this busy machine, growing with page size at a constant 6-8 SQL
statements: the concept query loads every concept's 1,536-number
embedding, which the list never shows. Filed rather than fixed here.

**Results:** 616 passed (617 - 2 obsolete checks + 1 new), `ruff
check`, `ruff format --check`, `mypy` clean. Frontend untouched.

## Rules (all [73] slices)

- Twins only while an unconverted caller needs the sync version; delete a
  sync function in the slice that removes its last caller.
- Tests that call converted code are async on `async_db`; arrange with
  `db` and commit. Frontend untouched.
- Reference production code: `git diff 260d7c2 9c42cfd -- <paths>` on
  `wip/73-async-remaining` (its twins are collapsed; adapt, do not copy).

## Definition of done

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] Log entry in this file; `status.md`, [67] and [73] updated
