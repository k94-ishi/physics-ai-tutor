---
title: "[98] Rename pass: drop the `async_` prefixes"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: one mechanical rename. No behaviour change.

## Scope

- `async_<name>` becomes `<name>`; `get_async_db` becomes `get_db`,
  `async_transaction` becomes `transaction`, etc. One commit on a green
  suite, nothing else in it.

## Acceptance criteria

- [x] No `async_` function names left in the app; suite green.

## Dependencies

- Blocked by: [88] (done 2026-11-16; no sync name is left to collide with)
- Blocks: [99]

## Log

### 2026-11-17 — done

**Kept as one commit**, as the issue asks: 81 prefixed functions plus
`get_async_db`, about 720 references in 66 rewritten files. Splitting a
mechanical rename would leave the code half-renamed between slices.

**Done by script, after a collision check.** Every app function named
`async_*`, `_async_*` or `get_async_db` was renamed (`get_async_db` to
`get_db`), including string references such as `monkeypatch.setattr`
targets. Before renaming, each file was checked for a bare use whose new
name was already bound to something else there (an import, a local
function, a variable); `module.async_x` uses cannot collide, since the
module prefix stays. Result: no collisions. Names the tests define
themselves (`async_create_user`, the `async_db` fixture, conftest's own
`async_engine`) were not touched.

**Left on purpose:** the module-level objects `async_client`
(`core/openai.py`, `core/deepseek.py`) and `async_engine`
(`database/database.py`), and SQLAlchemy's `async_sessionmaker`. The
criterion covers function names, and the tests use `engine` and
`async_engine` for their own two engines, so renaming the app's
`async_engine` to `engine` would give one name two meanings across tests
and app. Can be done later if wanted.

**Docs and comments:** two comments that described "the sync twin" and
this rename were removed. `docs/development.md` names the new functions,
except in the two-stacks section, which is history until [99] removes
it. Issue logs keep the names as they were at the time.

**Results:** 617 passed, `ruff check`, `ruff format --check`, `mypy`
clean. Frontend untouched.

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
