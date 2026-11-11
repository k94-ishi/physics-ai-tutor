---
title: "[79] Operator-tunable settings: limits, pools and timeouts move out of the code"
labels: [backend, config, operations]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [81]

## Summary

The values an operator may need to change in response to load, cost or
an incident are currently module-level constants, so changing one means
editing code and redeploying. Move exactly those into `Settings`, each
keeping its present value as the default.

## Motivation

Owner's observation (2026-11-11): there are many hard-coded parameters.
Not all of them should move ([80] argues some must not), but these
should, because the reason to change them is operational rather than
editorial: a cost scare, a traffic spike, a slow upstream, a connection
limit on the database plan.

Concretely, today an operator who wants to halve the anonymous ask
allowance, widen the connection pool, or shorten the AI review run
timeout has to open a pull request.

## Scope

Each becomes a setting with today's value as the default, documented in
`.env.template` and the `docs/development.md` table:

| Now | Where | Proposed variable |
| --- | --- | --- |
| `ANONYMOUS_AI_ASK_LIMITS = [(3, 3600), (10, 86400)]` | `api/dependencies.py` | `ANONYMOUS_AI_ASK_LIMITS` |
| `USER_AI_ASK_LIMITS = [(10, 3600), (30, 86400)]` | same | `USER_AI_ASK_LIMITS` |
| `ADMIN_AI_ASK_LIMITS = [(3000, 86400)]` | same | `ADMIN_AI_ASK_LIMITS` |
| `LOGIN_LIMITS = [(5, 60), (20, 3600)]` | same | `LOGIN_LIMITS` |
| `POOL_SIZE = 5`, `MAX_OVERFLOW = 10` | `database/database.py` | `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` |
| `RUN_TIMEOUT_MINUTES = 30` | `ai_review_service` | `AI_REVIEW_RUN_TIMEOUT_MINUTES` |
| `CLEANUP_PROBABILITY = 0.01` | `rate_limit_service` | `RATE_LIMIT_CLEANUP_PROBABILITY` |
| `GOOGLE_STATE_MAX_AGE_SECONDS = 600` | `api/v1/auth.py` | `GOOGLE_STATE_MAX_AGE_SECONDS` |
| LLM request timeouts | added in [70] | `LLM_REQUEST_TIMEOUT_SECONDS` |

- Rate-limit lists need a parse format that survives an env var. A JSON
  list of `[max, window_seconds]` pairs matches how
  `backend_cors_origins` is already supplied, so the mechanism exists.
- The settings are read where the value is used, not captured into a
  module constant at import, or an override will not take effect.
- Keep `AI_REVIEW_CONCURRENCY` ([72]) and the pool sizes consistent:
  document in one place how they interact with the database connection
  limit and the worker count ([75]).

## Acceptance criteria

- [ ] Every value above is settable by environment variable, and
      unsetting it reproduces today's behaviour exactly.
- [ ] A test proves at least one limit and one pool setting actually
      take effect when overridden (not merely that the field exists).
- [ ] No module-level constant shadows a setting.

## Out of scope

- Algorithm and presentation constants ([80]).
- Per-user or per-role overrides stored in the database; this is
  process-level configuration only.

## Technical notes

Rate limits are security-relevant (docs/security.md documents the
current numbers): making them configurable means a wrong value quietly
weakens the limiter, so the validation from [78] should cover them —
reject an empty list, a non-positive window, or a limit of zero. Update
`docs/security.md` to say the numbers are defaults rather than fixed.

## Dependencies

- Blocked by: none; easier after [78].
- Related: [70] adds the LLM timeout, [72] the concurrency limit, [74]
  the pool tuning, [75] the worker count.

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] `.env.template`, `docs/development.md` and `docs/security.md`
      updated
