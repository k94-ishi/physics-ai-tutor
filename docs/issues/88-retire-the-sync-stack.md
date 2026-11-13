---
title: "[88] Retire the sync stack: one engine, one session type, no async_ prefixes"
labels: [backend, async, refactor, docs]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], slice 7 of [73] (last)

## Summary

With every route and service converted ([83]-[87]), delete the sync
engine, session, dependency and transaction helper from the app, delete
the sync LLM clients and the remaining `async_` twins, and rename the
survivors to plain names. CLIs and the seed run on the async engine
through `asyncio.run`; Alembic keeps its own. This closes [73].

## Motivation

This is the step that pays: one pool per worker instead of two, which
is what [75] said stands between "two workers is the safe ceiling" and
four. It also ends the two-stack period from [69] - one session type,
one `transaction()`, one set of fixtures, one name per function - so
nothing can be written against the wrong stack again.

## Scope

- `database/`: delete the sync `engine`, `SessionLocal`, `get_db`,
  `transaction()` and `background_session()`. `database.py` builds one
  async engine with explicit pool numbers ([74] chooses the final
  values).
- `core/openai.py`, `core/deepseek.py`: delete the sync clients. Delete
  the sync twins left in `deepseek_service`, `embedding_service`,
  `translation_service`, `rag_service`, `rate_limit_service`, and in
  `query_embedding_repository`, `rate_limit_repository`,
  `question_ask_repository`, `background_claim_repository`. Check each
  for a last caller first (`eval_prompts` and the seed were the usual
  ones).
- One rename pass: `async_<name>` becomes `<name>` everywhere
  (about 40 functions), and the plumbing takes the plain names too:
  `get_async_db` becomes `get_db`, `async_transaction` becomes
  `transaction`, `async_background_session` becomes
  `background_session`, `AsyncSessionLocal` becomes `SessionLocal`,
  `async_engine` becomes `engine`. Update the `LLM_CALLS` list and the
  docs in the same change.
- Remaining scripts: `cli/export_seed.py`,
  `cli/export_seed_embeddings.py`, `database/init_db.py` move to
  `asyncio.run` on the async engine; `cli/create_user.py` already is.
  `alembic/env.py` is untouched (it builds its own engine from
  `DATABASE_URL`).
- Tests: the `db` fixture and the `create_user` bridge in `conftest.py`
  **stay, as test-only sync helpers** built on a test engine inside
  conftest. API tests arrange rows and assert on committed state
  through them, and rewriting ~300 of those for no gain is not the
  point of this track. Service and repository tests that *call*
  converted code use `async_db`. The `client` fixture overrides only
  the one session dependency; `_background_translation_uses_test_db`
  patches only the one factory. `tests/` gets the explicit exemption in
  the architecture test.
- `test_architecture.py` end state: no `sqlalchemy.orm.Session`
  annotation and no `sessionmaker` outside `database/`, `alembic/`,
  `tests/`; the "who still uses the sync LLM clients" test becomes "the
  two client modules export only async clients"; the "async code never
  uses the sync transaction helper" test and the [82] allowlist with
  its companion test are removed because there is nothing left for them
  to guard. Each remaining check keeps its self-test that it can still
  catch a violation.
- `docs/development.md`: remove "Two stacks during the async
  migration" and fold what remains (fixture names, the lazy-load rule,
  `expire_on_commit=False`) into the layers section; update the test
  layout table and the `conftest` patch-helper paragraph; in "Running
  more than one worker", the budget becomes one pool per worker
  (`pool_size + max_overflow`, 15 worst case) and the ceiling note says
  four is reasonable once [74] has set the numbers.
- Measure: repeat the [75] worker table (800 requests to
  `/questions?size=50` at concurrency 32, one and two workers) and
  record connections per worker before and after; repeat the [82] probe
  (60 concurrent asks) to confirm no regression.

## Acceptance criteria

- [ ] `rg "SessionLocal|sessionmaker|get_db|create_engine"` in
      `backend/physics_ai_tutor` matches only `database/`; Alembic and
      tests excepted by path.
- [ ] One engine and one pool per process at runtime; pool settings
      documented in one place.
- [ ] No function in the app is named `async_*`; the LLM seam list in
      `test_architecture.py` has one name per seam.
- [ ] The architecture test enforces the end state and fails on a
      planted sync `Session` annotation in a service.
- [ ] Behaviour identical: the whole suite green with no test deleted
      except the three checks named above; CLIs and the seed verified
      by `test_cli.py` and `test_seed.py`.
- [ ] Connection counts per worker recorded in the Log; the worker
      ceiling note in `docs/development.md` updated.

## Out of scope

- Choosing the final pool numbers and the pgvector index ([74]).
- Raising `WEB_CONCURRENCY` on Render (the owner's switch, at the
  track's single deploy).
- Any API or behaviour change.

## Technical notes

Reference on `wip/73-async-remaining`:
`git diff 260d7c2 9c42cfd -- backend/physics_ai_tutor/database backend/physics_ai_tutor/core backend/physics_ai_tutor/cli/{export_seed,export_seed_embeddings}.py backend/physics_ai_tutor/database/init_db.py backend/tests/test_architecture.py`.
The WIP already made the engine and name decisions this issue
describes; its `conftest.py` is **not** the reference, because it tried
to move the arrange/assert fixtures to async and that is where most of
its 118 failures came from.

Do the rename as one mechanical commit on a green suite, separate from
the deletions, so a reviewer can verify it with a search rather than by
reading. Run the suite with `-W error::RuntimeWarning` already in place
([83]).

## Dependencies

- Blocked by: [83], [84], [85], [86], [87].
- Blocks: raising the worker count beyond two ([75] note); the
  pre-deploy check at the end of [67]. Closes [73].

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Frontend untouched; CI green
- [ ] `docs/development.md` describes only the async stack; the
      "Running more than one worker" budget updated
- [ ] Before/after connection counts in this issue's Log
- [ ] [73]'s acceptance boxes ticked and [73] closed in `status.md`
