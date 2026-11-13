---
title: "[73] Asynchronize the rest (umbrella for [83]-[99]): every route on the async stack; app keeps no sync engine"
labels: [backend, async, refactor, epic]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67]

## Summary

Convert everything [70] and [72] did not cover, until the application
serves every request through the async stack, then remove the sync
engine from the app. CLIs and Alembic: Alembic keeps its own sync
engine; CLIs run the async services through `asyncio.run`.

**Re-scoped 2026-11-13.** This issue is now the umbrella: the work is
in seven slices, one merged and six open as their own issues. It stays
open until [88] lands and the acceptance criteria below are ticked.

## Motivation

Finishes the owner's "asynchronize the whole system" goal and ends the
two-stack period from [69]: one session type, one `transaction()`, one
set of fixtures, and no leftover routes that can still tie up threads
(admin bulk actions, review endpoints with translation side effects).
Half-converted codebases rot; this closes the migration. It is also
what halves the connection demand per worker ([75]), which is what
stands between two workers and four.

## Scope: the slices

Each slice is its own PR with the suite green after it. Order is by
traffic first, then by which sync functions can be deleted soonest.

| # | Issue | What converts | Status |
| --- | --- | --- | --- |
| 1 | (this issue, 260d7c2) | Auth, users, sessions | merged 2026-11-12 |
| 2 | [83] | Public question reads | done 2026-11-13 |
| 3 | [84] | Asynchronize the public tag search (GET /concepts) | done 2026-11-13 |
| 4 | [89] | Asynchronize the admin tag editor reads: list and detail | done 2026-11-13 |
| 5 | [90] | Asynchronize the admin tag editor writes: gloss, words, merge, split | done 2026-11-13 |
| 6 | [91] | Asynchronize concept extraction and the re-extract route | done 2026-11-13 |
| 7 | [85] | Asynchronize the review routes: review, bulk review, history | open |
| 8 | [92] | Asynchronize the fill-translations route (POST /questions/translate) | open |
| 9 | [86] | Asynchronize delete and bulk delete | open |
| 10 | [93] | Asynchronize create and update (prepare/apply) | open |
| 11 | [94] | Asynchronize JSONL import | open |
| 12 | [95] | Seed and translation CLIs on the async services; delete the sync translation half | open |
| 13 | [87] | Asynchronize the usage dashboard and the agreement report | open |
| 14 | [96] | Asynchronize the review dataset export | open |
| 15 | [97] | Asynchronize AI review runs; one ai_review_service | open |
| 16 | [88] | Delete the sync engine, sync LLM clients and remaining sync twins | open |
| 17 | [98] | Rename pass: drop the async_ prefixes | open |
| 18 | [99] | Async end state: architecture test, docs, connection budget (closes [73]) | open |

Chains: concepts [84]→[89]→[90]→[91], review [85]→[92], writes [86]→[93]→[94]→[95], admin stats [87]→[96]→[97], end [88]→[98]→[99]. [87] needs only [83] and can run beside the concept chain. [76] (batch embeddings on import) is
recommended before [86].

## Acceptance criteria (the end state, ticked by [88])

- [ ] No route resolves a sync `Session`; `rg "SessionLocal"` outside
      `database/`, `alembic/`, `tests/` finds nothing app-side.
- [ ] One engine, one pool at runtime; pool settings documented.
- [ ] Architecture test enforces the end state.
- [ ] Behaviour identical: strict-language rule ([53]), admin fallback,
      review history, bulk actions, exports — existing tests are the net.

## Out of scope

- Any feature or API change (the `helath_check` operationId typo stays,
  as in Track E).
- Frontend changes.

## Rules shared by every slice

- **Twins until the last caller goes.** A function used by both
  converted and unconverted callers keeps its sync version and gains
  `async_<name>` ([70]). The slice that removes the last sync caller
  deletes the sync version; [88] drops the prefixes. Where a twin would
  duplicate a rule (status filter, strict-language naming), extract and
  share the rule.
- **Convert callees before callers; never bridge with
  `run_in_executor`.** A slice is router, services and repositories of
  one call chain, plus any CLI or script that calls them.
- **No LLM call inside a transaction** ([82]): prepare, then apply. The
  allowlist in `test_architecture.py` only shrinks.
- **Read scalars off ORM rows before a transaction that might roll
  back** ([70]); use `selectinload` for relationships the sync code
  loaded lazily.
- **The WIP branch is a reference, not a source.**
  `wip/73-async-remaining` (9c42cfd, directly on top of slice 1) holds a
  finished, type-checked conversion of all 51 production files. Each
  slice issue names the `git diff 260d7c2 9c42cfd -- <paths>` to look
  at. The branch collapsed every twin at once, which is exactly why its
  suite was red; take bodies from it, keep the twins the slice still
  needs, and write the test changes fresh. Its `conftest.py` is not the
  reference ([88] explains).
- Before each PR: pytest, ruff, mypy; frontend checks untouched but CI
  green. Production `DATABASE_URL` and real API keys are never touched.

## Technical notes

~15 repositories, ~25 services, 9 routers, 598 tests: expect the test
churn to dominate every slice. An un-awaited `db.commit()` on an
`AsyncSession` keeps its row locks and deadlocks the *next* HTTP call
rather than failing — [83] makes `RuntimeWarning` an error in pytest
so this shows up as a failure, not a hang. A scripted `def` →
`async def` pass must count only the awaits belonging to the function
itself, not to nested ones.

## Dependencies

- Blocked by: [70], [72] (done).
- Blocks: raising the worker count past two ([75]); the end-of-track
  pre-deploy check ([67]).

## Definition of done

- [ ] [83]-[88] closed
- [ ] `docs/development.md` backend-layers section describes only the
      async stack; dual-stack notes removed
- [ ] This issue closed in `status.md`

## Log

### 2026-11-13 — turned into an umbrella; six slice issues filed

The 2026-11-12 entry below proposed five slices inside this issue but
left them as prose. Checked against the code today (HEAD cb87d57):
auth/users/sessions are async; `questions.py` has 5 of 6 routes sync,
`admin_questions.py` 10 of 10, `admin.py` 7 of 7, `concepts.py` 10 of
10. Still fully sync: `question_presentation`, `recommendation`,
`prerequisite`, `question_review`, `review_export`, `review_metrics`,
`stats` services and the `concept_term`, `question_review`,
`review_metrics`, `stats` repositories; twin pairs remain in eight
services and six repositories.

Changes from the 2026-11-12 proposal:

- The proposal's "slice 2, auth and users" was the slice already
  merged; removed.
- "Admin" (28 routes, 8 services, 8 repositories, ~170 tests) was the
  same too-big shape again. It is now four issues by call chain:
  concepts [84], review workflow [85], content writes [86], stats and
  runs [87]. Each has a single-caller repository it can convert
  outright, which is what keeps twins few.
- "CLIs" is no longer a slice. A slice cannot merge with its CLI
  callers broken (`test_cli.py`, `test_seed.py` run them), so each CLI
  moves with the service it calls; only `export_seed`,
  `export_seed_embeddings` and `init_db` are left for [88].
- The WIP branch is named in every slice as the reference for the
  production side, with the warning that its collapsed twins and its
  conftest are not to be taken as is.
- Two guards added early: `RuntimeWarning` as a test failure ([83]) and
  a pinned test for the legacy create form ([86]).

Not run here: the suite (this worktree has no test database container
running); the slice sizes are estimates from grep counts, listed in
each issue.

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
attached. It should have been five issues from the start.

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

### 2026-11-13 — slices split again

[83] (22 files, 35 tests) was still too big for the owner. Each remaining slice is now one route group or one script group, about ten tests or fewer: [84]-[88] were narrowed and [89]-[99] filed.
