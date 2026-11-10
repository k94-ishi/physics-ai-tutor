---
title: "[61] Tag domain: one package for tags, legacy name columns removed ([55] stage 5)"
labels: [refactor, backend, migration]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [57]

## Summary

Tags (code name: concepts) are spread over `concept_service`,
`concept_sense_service`, three repositories and the `name_ja`/`name_en`
mirror columns that 9 modules still read. Make it one package with one
read model, then finish [55] by dropping the mirrors.

## Scope

- `services/tags/`: `extraction.py` (prompt call, parsing, levels),
  `matching.py` (sense resolution), `terms.py` (add/edit/merge/split),
  `search.py`, `translation.py`. The import cycle between the two
  current modules disappears.
- Every reader uses terms (`label(concept, lang)`); then a migration
  drops `concepts.name_ja` / `name_en` (downgrade rebuilds them from
  preferred terms).
- Seed format unchanged (`"<ja> | <en>"` pairs stay the exchange format).
- Naming: keep `concept` in code and tables (decided 2026-11-10); only
  module names under `services/tags/` say "tag" if the owner prefers -
  decide at the start of this issue.

## Acceptance criteria

- [ ] No code reads `name_ja`/`name_en`; migration up/down verified.
- [ ] Seed round-trip tests and [55] tests pass unchanged.

## Dependencies

- Blocked by: [58]; the migration only after [54] (production has the
  tag tables).
