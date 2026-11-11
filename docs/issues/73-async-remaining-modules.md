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
