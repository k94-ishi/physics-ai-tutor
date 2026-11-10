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
