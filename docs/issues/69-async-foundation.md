---
title: "[69] Async foundation: engine, session, transaction, and test plumbing"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P1
---

**Priority:** P1  **Milestone:** M1 — Student value  **Track:** [67]

## Summary

Add the async database stack next to the sync one: an async engine and
sessionmaker, an async `get_db` dependency, an async `transaction()`,
an async `background_session()`, and the pytest plumbing to test async
services and repositories. Convert one small vertical slice (`/health`)
to prove the whole path works. No user-visible change.

## Motivation

Every later conversion ([70], [72], [73]) needs this plumbing. Doing it
with a tiny route first keeps the risky part (engine config, session
lifecycle, transaction semantics, test fixtures) in one small PR instead
of buried inside the big hot-path change.

## Scope

- `database/database.py`: `create_async_engine` beside the sync engine.
  SQLAlchemy 2 drives psycopg3 async on the same
  `postgresql+psycopg://` URL, so `DATABASE_URL` and `.env` templates do
  not change and no new driver is added.
- `database/dependency.py`: `get_async_db` yielding `AsyncSession`.
- `database/transaction.py`: `async def` variant with identical
  semantics — commit on success, rollback + `Rolling back transaction:
  operation=...` log + re-raise on error. It stays the only code that
  commits or rolls back ([59] rule).
- `database/session.py`: async `background_session()`; tests keep one
  place to point at the test database.
- Tests (`conftest.py`): an `async_db` fixture (same reset-before-test
  behaviour as `db`), anyio/pytest-asyncio wiring, and async-capable
  mocks where a converted module needs them. `TestClient` already
  drives async routes, so API tests do not change style.
- `tests/test_architecture.py`: extend the rules to the async stack
  (routers never open sessions; only the two `transaction()` variants
  commit); forbid sync `SessionLocal` in converted modules.
- Convert `/health` (router + `health_service`) as the proof slice.
- Document the conventions in `docs/development.md` (backend layers
  section): how a converted module gets its session, which fixture to
  use, "a slice is converted whole or not at all".

## Acceptance criteria

- [x] `/health` served through `AsyncSession`; suite green.
- [x] Sync and async stacks coexist; unconverted modules are untouched.
- [x] Transaction rollback behaviour covered by a test on the async
      variant (same guarantees as the sync one).
- [x] Engine pool settings explicit and documented (size, `pool_pre_ping`
      for the Supabase pooler path).

## Out of scope

- Converting any LLM-calling code ([70]) or background task ([72]).
- Removing the sync engine ([73] does that for the app; CLIs and
  Alembic keep sync forever — Alembic's `env.py` is unaffected).

## Technical notes

Two engines mean two pools against the same database; keep the async
pool small until [73] retires the sync one, and note the combined total
stays below Supabase's connection limit. `expire_on_commit=False` should
carry over to the async sessionmaker — services return ORM objects after
commit. pgvector's SQLAlchemy types work unchanged on `AsyncSession`.

## Dependencies

- Blocked by: [68] (baseline first).
- Blocks: [70], [72], [73].

## Definition of done

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] No schema change (no migration needed)
- [x] `docs/development.md` updated (layers/transactions, test fixtures)

## Log

### 2026-11-11 — done

Async stack added beside the sync one; `/health` and `/db-health`
converted as the proof slice. 550 tests pass (was 541), ruff and mypy
clean. Checked live on a local stack: `/db-health` answers through
`AsyncSession` while `/questions` still answers through the sync
session, in the same process.

**What landed.** `async_engine` + `AsyncSessionLocal`
(`database/database.py`), `get_async_db` (`dependency.py`),
`async_transaction` (`transaction.py`), `async_background_session`
(`session.py`), `health_service.check_database` and both health routes,
`tests/test_async_foundation.py` (7 tests), and the async fixtures
(`async_db`, `anyio_backend`, an async `get_async_db` override, an
async background factory patch).

**One new dependency: greenlet**, via `sqlalchemy[asyncio]`. Not
optional and not a driver change — SQLAlchemy uses greenlet to drive its
ORM internals from async code, and `create_async_engine` raises
`ValueError: the greenlet library is required` without it. The driver
(`psycopg`) and `DATABASE_URL` are unchanged, as planned. Locked in
`uv.lock`; `uv sync` also pruned four packages (`deep-translator`,
`requests`, `soupsieve`, `urllib3`) that were in the venv but never
declared in `pyproject.toml` — leftovers of a deleted
`concept_name_translation_service`, confirmed unreferenced by any source
file.

**Pools are now explicit** on both engines: `pool_size=5`,
`max_overflow=10` (SQLAlchemy's previous implicit defaults, so no
behaviour change), plus `pool_pre_ping=True` so a connection the server
dropped is caught at checkout instead of failing a request. Written as
`POOL_SIZE` / `MAX_OVERFLOW` constants with a test pinning them, because
until [73] the two pools add up against one connection limit. [68]
established the pool is not today's bottleneck; [74] tunes the numbers.

**Three architecture rules added**, each with a self-check that it can
still catch a violation:

1. Only `database/` and script entry points (`cli/`, `database/seed.py`)
   may build a session factory.
2. An `async def` must not use the sync `transaction()`. This is the
   dangerous shape of the whole migration: `with transaction(db, ...)`
   on an `AsyncSession` calls `commit()` without awaiting it, so the
   block looks correct and writes nothing. A static check is worth more
   than hoping a test notices the missing row.
3. The existing commit/rollback rule now also catches `await
   db.commit()` (the AST walk already saw through `ast.Await`;
   `test_the_checks_catch_a_violation` now proves it).

**Decisions worth recording.**

- The `client` fixture gives a converted route **its own** `AsyncSession`
  rather than sharing the test's `db` object, which is impossible across
  the two session types. Committed rows are what a real request sees
  anyway, and every write in this codebase goes through `transaction()`,
  so nothing in the suite depended on sharing uncommitted state.
- Async tests use anyio's pytest plugin (ships with anyio, already a
  Starlette dependency) rather than adding `pytest-asyncio`. Verified
  the tests really execute, not silently skip, by running them under
  `-W error::RuntimeWarning`.
- `/health` itself needs no database, so `/db-health` is the part that
  actually exercises the async session; both were converted so the
  module has one style.

**Not done here, by design:** no LLM-calling code ([70]), no background
task ([72]), and the sync engine is still the app's main path. The next
step converts the ask and search slice.
