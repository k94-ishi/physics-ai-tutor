---
title: "[73] Asynchronize the rest: all routers, services, repositories; app keeps no sync engine"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67]

## Summary

Convert everything [70] and [72] did not cover — question reads/writes/
review, admin, auth, users, concepts, stats — slice by slice, until the
application serves every request through the async stack. Then remove
the sync engine from the app; CLIs and Alembic keep their own sync
sessions, wrapping async services with `asyncio.run` where they call
them.

## Motivation

Finishes the owner's "asynchronize the whole system" goal and ends the
two-stack period from [69]: one session type, one `transaction()`, one
set of fixtures, and no leftover routes that can still tie up threads
(admin bulk actions, review endpoints with translation side effects).
Half-converted codebases rot; this closes the migration.

## Scope

**Re-scoped 2026-11-12 after attempting it in one pass** — see the Log.
Slice 1 is merged; slices 2-5 below are each their own issue-sized piece
of work, because the test-suite migration turned out to dominate and a
single change cannot keep the suite green across it.

Slices, each its own PR, suite green after each (order by traffic):

1. Public question reads: list/detail/related/prerequisites +
   `question_read_service`, `question_presentation_service`,
   `recommendation_service`, `prerequisite_service`, `concept` reads.
2. Auth and users: `auth_service`, `google_auth_service` (its outbound
   HTTP calls become async too), `user_service`.
3. Admin: `admin.py`, `admin_questions.py`, review/write/translation
   services, stats, review metrics, exports, concept admin.
4. Cleanup: drop `get_db`/sync `SessionLocal` from the app path, drop
   the sync `transaction()` once unused, tighten
   `test_architecture.py` to forbid sync sessions outside `cli/` and
   `alembic/`, remove sync conftest fixtures that no longer have users.
5. CLIs (`create_user`, `translate_missing`, `review_pending`,
   `eval_prompts`, exporters, backfills): keep working; where a service
   went async they call `asyncio.run(...)`. The nightly workflow ([26])
   runs unchanged.

## Acceptance criteria

- [ ] No route resolves a sync `Session`; `rg "SessionLocal"` outside
      `cli/`, `alembic/`, `tests/` finds nothing app-side.
- [ ] One engine, one pool at runtime; pool settings documented.
- [ ] Architecture test enforces the end state.
- [ ] Behaviour identical: strict-language rule ([53]), admin fallback,
      review history, bulk actions, exports — existing tests are the net.

## Out of scope

- Any feature or API change (the `helath_check` operationId typo stays,
  as in Track E).
- Frontend changes.

## Technical notes

This is mostly mechanical but wide (~15 repositories, ~25 services, 9
routers, 522 tests): expect the test churn to dominate. Convert callees
before callers inside a slice; never bridge with `run_in_executor`.
Watch lazy loading — `AsyncSession` raises on implicit IO, so any
relationship the sync code loaded lazily needs explicit
`selectinload`/explicit queries; the existing repository tests catch
most of these. `question.text()`-style pure helpers are unaffected.

## Dependencies

- Blocked by: [70], [72].
- Blocks: nothing, but ends the dual-stack period from [69].

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Frontend suite still green in CI (no contract change)
- [ ] `docs/development.md` backend-layers section describes only the
      async stack; dual-stack notes removed

## Log

### 2026-11-12 — slice 1 merged; the rest re-scoped

**Merged (260d7c2):** auth, users and sessions. `user_repository`,
`auth_service`, `user_service`, `google_auth_service`,
`ask_history_service`, the auth and users routers, and every auth
dependency. `api/dependencies.py` now holds no sync session. The Google
token exchange was a blocking `urllib` call, which on an async server
would stall every other request while Google was slow; it is an awaited
`httpx2` call now (httpx2 ships with the openai SDK, so no new
dependency). 598 tests green.

**Attempted and set aside:** the rest, in one pass. The production side
*was* finished and is preserved on the branch `wip/73-async-remaining`
(9c42cfd), verified by mypy at 119 files with zero errors and ruff
clean:

- all 15 repositories async, with ~73 `Query` chains rewritten as 2.0
  `select()`
- all 27 services async, with the sync/async twin pairs from [70]/[72]
  collapsed to one implementation each
- all 9 routers async
- all 11 CLIs, the seed and `init_db` wrapped with `asyncio.run`
- the sync engine, `SessionLocal`, `get_db` and the sync `transaction()`
  **deleted** — one engine, one pool, which halves the per-worker
  connection demand [75] measured

**Why it was not merged:** the test suite reached 460 of 598. The
remaining ~118 failures are mechanical but each needs judgement, and a
red suite is exactly the wrong thing to merge here — the suite *is* the
safety argument for a change that touches 51 production files and claims
no behaviour change. Forcing it green in bulk is also how a
security-relevant assertion gets silently dropped; this track has
already seen tests pass vacuously twice ([71], [72]), both caught only
because the suite was otherwise trustworthy.

**The real lesson:** the scope was wrong, not the approach. "Convert
everything that remains" is 9,000 lines across 51 files with ~600 tests
attached. It should have been five issues from the start. The
re-scoped slices above are the proposal.

**Two traps, recorded for whoever finishes this:**

1. An un-awaited `db.commit()` on an `AsyncSession` silently leaves the
   transaction open and keeps its row locks, so the *next* HTTP call
   deadlocks rather than failing. The suite hung instead of erroring,
   twice, before this was found. A lint rule for un-awaited session
   calls in tests would pay for itself.
2. A scripted `def` → `async def` pass must count only the awaits that
   belong to the function itself, not to a nested one. Walking the whole
   subtree made `conftest.create_user` async (it is a deliberate sync
   bridge) and, on the corrective pass, turned awaitable stubs back into
   sync ones — both silent until tests failed oddly.

**Also found while converting**, worth keeping whichever way this goes:

- The async `create_question` added in [70] had dropped the legacy
  single-language `question=/answer=/language=` form that the seed and
  several tests use. Restored on the WIP branch.
- `concept_service.translate_missing_name` held a connection across its
  LLM call — the [82] fault again, in a shape the lexical tripwire
  cannot see because the call sits inside an *implicit* transaction
  opened by preceding reads rather than a `with` block. Fixed in [72];
  this is the second instance, so the runtime probes are the load-bearing
  check, not the AST one.
