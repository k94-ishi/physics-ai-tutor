---
title: "[78] Config hygiene: fix the defaults, validate at startup, end the template drift"
labels: [backend, config, operations]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [81]

## Summary

Tidy `core/config.py` itself: fix the wrong defaults it already carries,
reject impossible or unsafe values when the app starts instead of hours
later, and make `.env.template` and the `docs/development.md` table match
the code so an operator can trust either one.

## Motivation

Owner's observation (2026-11-11): the codebase has many parameters and
they are hard-coded. Before moving anything into settings ([79]), the
settings file should be worth trusting. Two concrete problems found
while reading it:

- `backend_cors_origins` defaults to `["http://loaclhost:8000"]` — a
  typo for `localhost`, and the wrong port for a frontend origin. It is
  always overridden in practice, which is exactly why nobody noticed.
- Nothing validates values at startup. A malformed
  `AI_REVIEW_OFFPEAK_START`, a `SAME_SITE=none` without
  `COOKIE_SECURE=true` (a cookie browsers will reject), or a short
  `JWT_SECRET_KEY` in production all fail later and indirectly, if at
  all.

## Scope

- Fix the `backend_cors_origins` default (and re-check every other
  default against what a real deployment uses).
- Validate at construction, with Pydantic validators, so a bad value
  stops the process with a clear message:
  - `ai_review_offpeak_start` / `_end` parse as `HH:MM`.
  - `same_site="none"` requires `cookie_secure=True`.
  - In a non-development `environment`: `jwt_secret_key` is not a
    placeholder and is long enough, `cookie_secure` is true, and
    `backend_cors_origins` is not the default.
  - Numeric settings are positive where zero makes no sense
    (`jwt_access_token_expire_minutes`, `deepseek_max_tokens`,
    `ai_review_daily_cap`).
- Group the fields with short comments (they are already roughly
  grouped) and make sure each has a one-line explanation of what it
  does, not what it is.
- A test that `.env.template`, the `docs/development.md` environment
  table and `Settings` list the same variable names — the drift check,
  so the three cannot diverge again.

## Acceptance criteria

- [ ] A malformed off-peak window, `SAME_SITE=none` without secure
      cookies, and a placeholder JWT secret in production each fail at
      startup with a message naming the variable.
- [ ] Development defaults still start with only the documented required
      variables set.
- [ ] Template, docs table and `Settings` agree; a test fails if one
      gains a variable the others lack.

## Out of scope

- Moving any hard-coded constant into settings ([79]).
- Tuning constants that stay in code ([80]).
- Secret management or rotation.

## Technical notes

`Settings()` is constructed at import, so a validation failure is a
startup crash — which is the point, but it also means the error message
is the only thing the operator sees. Make each message name the variable
and the expected shape. Tests construct `Settings` directly with
explicit values rather than relying on the ambient `.env`.

## Dependencies

- Blocked by: none.
- Blocks: [79] is easier after this, but they are independent.

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] `docs/development.md` environment table and `backend/.env.template`
      updated together
