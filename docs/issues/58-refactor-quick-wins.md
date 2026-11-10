---
title: "[58] Refactor quick wins: docs drift, shared helpers, faster seed tests"
labels: [refactor, docs, testing]
milestone: M1 Student value
priority: P1
---

**Priority:** P1  **Milestone:** M1 — Student value  **Track:** [57]

## Summary

Small, low-risk fixes that make the later steps easier.

## Scope

- `CLAUDE.md`: replace the stale copy with a pointer to `AGENTS.md`
  (README already claims it links there).
- One text-normalisation helper (`core/text.py`): NFKC + whitespace,
  with a `casefold` variant for term keys; replace the three copies.
- One `tag_pair_text(ja, en)` helper used by extraction, `export_seed`
  and `export_seed_embeddings` (the three must agree byte for byte, or
  seed vectors miss).
- `is_admin(current_user)` in `api/dependencies.py`; routers stop
  re-implementing it.
- Seed tests: seed once per test session into a template database (or
  a module-scoped fixture) instead of 7 full seeds; target backend suite
  under 3 minutes.

## Acceptance criteria

- [ ] No behaviour change; all checks pass.
- [ ] `grep` finds one definition of each helper.
- [ ] Backend suite time recorded before/after in the Log.

## Dependencies

- Blocks: [59]-[61] (they use the helpers)

## Log

### 2026-11-10 - done

- `CLAUDE.md` is now `@AGENTS.md` (the stale copy lacked the prompt rules
  and the vitest step), the same as `frontend/CLAUDE.md`.
- `core/text.py`: `normalize_text` (NFKC + whitespace, the query cache
  key) and `normalize_key` (+ case folding, the concept term key) replace
  `embedding_service.normalize_query`, `concept_sense_service.normalize_term`
  and `concept_repository.normalize`. `concept_pair_text` (the embedded
  text that seed vectors key on) and `concept_line` (the `<ja> | <en>`
  seed format) replace three private copies. The two differ on purpose:
  a missing side is dropped from the embedded text but kept as an empty
  slot in the seed line, so the parser assigns it to the right language.
- `api.dependencies.is_admin` replaces the router copies.
- Seed tests moved to `tests/test_seed.py`: one seed per module with
  OpenAI and DeepSeek forbidden, then read-only assertions (6 tests
  instead of 7 seeds). Backend suite 5:56 -> 4:27 (520 -> 519 tests).
  The 3-minute target was **not** met: the remaining seed takes 147 s
  inside the suite but ~25 s alone - moved to [66] with the measurements.
- Checks: pytest 519, ruff, mypy, lint, tsc, vitest 166 pass. The
  frontend build was not re-run (no frontend change; a host build breaks
  the running dev container, see docs/development.md).
