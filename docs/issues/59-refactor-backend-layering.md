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
