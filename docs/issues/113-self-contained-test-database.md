---
title: "[113] Self-contained tests: a temporary database per run, settings isolated from .env"
labels: [backend, testing]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** found during [67]

## Summary

`uv run pytest` works with no running database and no environment
variables: the suite starts its own PostgreSQL + pgvector container and
cannot pick up a real database or API key from `backend/.env`.

## Motivation

Owner's request (2026-11-16): a test run should be self-contained.
Until now the suite needed a pre-started `postgres-test` container and,
in practice, exported settings. Two problems followed:

- Sessions on one machine shared test databases: twice ([108], [112])
  another session ran against this work's database, and only the
  suite's advisory lock stopped the clash.
- The settings read `backend/.env`, so a plain run let the app's engine
  and AI keys come from that file (which may name production). Tests mock
  every AI call and redirect every session, but one miss would have
  reached a real service.

## Scope

- `tests/isolated_environment.py`, called first by `conftest.py`:
  forces `DATABASE_URL`, the OpenAI/DeepSeek keys and base URLs; unless
  `TEST_DATABASE_URL` is set, starts a `pgvector/pgvector:pg17` container
  via `testcontainers` (new dev dependency) and removes it at session end.
- Orphan cleanup for killed runs, by owner process id and host label.
- `tests/test_isolated_environment.py` pins the guarantees.
- `docs/development.md` and `docs/database.md` describe it.

## Acceptance criteria

- [x] `env -i HOME=$HOME PATH=$PATH uv run pytest` passes (617 tests).
- [x] No container is left after a normal run; a killed run's container
      is removed by the next run; a live run's container is never removed.
- [x] `TEST_DATABASE_URL` still selects an existing database (CI, compose)
      and then no container starts.

## Out of scope

- CI keeps its service container through `TEST_DATABASE_URL`; switching
  it to the temporary container is possible but changes nothing for
  correctness.

## Dependencies

- Blocked by: none
- Blocks: none

## Log

### 2026-11-16 — done

**Design.** A container rather than a Postgres bundled in a pip package:
it is the exact image dev and CI use, pgvector included, and Docker is
already required for local work. The settings step must run before the
app is imported (settings are read once, at import), so it is the first
statement of `conftest.py`; `E402` is allowed for that one file. A `-p`
plugin was considered and rejected: pytest imports it before it sets up
the import path for `tests`.

**The reaper did not work here, so it is off.** testcontainers normally
starts a Ryuk container that removes leftovers when the test process
dies. Tested by killing a run with `SIGKILL`: Ryuk logged no client
connection (Docker Desktop's port forwarding), timed out, and exited
removing nothing. Instead each container is labelled with its run's
process id and host, and a starting run removes only containers whose
process is gone on this machine. Verified three ways: a killed run's
container is removed by the next run; two runs at once (a full suite
and a short one) leave each other alone and both pass; a normal run
leaves nothing.

**Shutdown noise fixed.** Stopping the container from
`pytest_unconfigure` logged through closed streams; it now stops at the
end of the session-wide database fixture, and the Docker client loggers
are quieted for the `atexit` fallback.

**Override path verified** against a throwaway server started by hand:
5 tests passed and no container was created.

**Results:** 617 passed with an empty environment (614 + 3 new), `ruff
check`, `ruff format --check`, `mypy` clean (the Docker client is reached
through testcontainers' typed wrapper, so no stub package is needed).
Frontend untouched.
