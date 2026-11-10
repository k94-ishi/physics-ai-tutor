---
title: "[59] Backend layering: routers call services only; transactions in one place"
labels: [refactor, backend]
milestone: M1 Student value
priority: P1
---

**Priority:** P1  **Milestone:** M1 — Student value  **Track:** [57]

## Summary

Restore the AGENTS.md rule (router -> service -> repository) where it
slipped, and make commit/rollback a service-level concern.

## Scope

- Move the direct DB/repository calls out of `api/v1/concepts.py`
  (8), `admin.py` (2), `ai.py` (2), and the repository imports in
  `questions.py` and `users.py`, into services.
- Repositories never commit (`query_embedding_repository` does today).
- Services own the unit of work: one `commit` per use case, via a small
  `transaction(db)` context manager, instead of 20 scattered commits.
  Background tasks (`background_translation_service`, `post_generation_tasks`,
  AI review runs) keep their own sessions, created in one helper.
- Router functions shrink to: parse, authorise, call one service, map
  domain errors to HTTP. `ask_ai` (101 lines) is the main case: move the
  cache/RAG/generate/record flow into `ai_service.ask`.
- A test (or ruff rule via an import check) that fails if `api/` imports
  `repositories` or `models` for queries.

## Acceptance criteria

- [ ] No router touches `db.query`/`db.get`/`db.commit` or a repository.
- [ ] No repository calls `commit`.
- [ ] All checks pass; API responses unchanged (existing API tests).

## Dependencies

- Blocked by: [58]
- Blocks: [60]

## Log

### 2026-11-11 - done

- **Transactions in one place**: `database/transaction.py` `transaction(db,
  operation)` replaces 47 scattered `commit()`/`rollback()` calls in 11
  modules (10 services and the seed). It keeps the existing log line
  (`Rolling back transaction: operation=...`). Best-effort steps (saving an
  AI answer, recording an ask, cache bookkeeping, per-question re-extraction
  and AI review) wrap the `with` in their own `try`, so a failure is still
  swallowed and logged exactly as before.
- **Repositories never commit**: `query_embedding_repository` only flushes
  now; the insert race (two identical searches) is handled in
  `embedding_service`, the same fallback as before.
- **AI review runs** ([34] semantics kept): `start_run` is one transaction,
  so refusing to start still undoes the timed-out-run reaping, and a lost
  race still surfaces as `RunInProgressError`; `execute_run` commits once
  per question, so progress polling is unchanged.
- **Routers**:
  - `ai.py` 101-line `ask_ai` -> `services/ai_service.ask`; the router is
    19 lines.
  - `concepts.py`: six commits and model/repository use -> one-transaction
    editor use cases in `concept_sense_service` with not-found errors.
  - `admin.py`: run queries and the background runner -> `ai_review_service`.
  - `questions.py`, `users.py`, `api/dependencies.py`: repository calls ->
    service calls.
  - `health.py`: the `SELECT 1` -> `health_service` (found by the new test;
    my first search had missed `db.execute`).
- **Background sessions**: `database/session.background_session()` used
  by every background task; the test fixture patches one place instead of three.
- **Guard**: `tests/test_architecture.py` (routers import no repositories /
  session factories and make no session calls; only `transaction()` commits
  or rolls back; plus a self-check that the rules match a planted
  violation - verified by planting one in `users.py`).
- **No behaviour change**: the OpenAPI schema is byte-identical to before
  (compared `app.openapi()` of HEAD and the branch). Fixing the
  `helath_check` typo would change one operationId, so it was reverted and
  left for a separate change.
- Checks: pytest 525 (26-40 s), ruff, ruff format, mypy.
