---
title: "[61] Concept domain: one package for concepts, legacy name columns removed ([55] stage 5)"
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

- `services/concepts/`: `extraction.py` (prompt call, parsing, levels),
  `matching.py` (sense resolution), `terms.py` (add/edit/merge/split),
  `search.py`, `translation.py`. The import cycle between the two
  current modules disappears.
- Every reader uses terms (`label(concept, lang)`); then a migration
  drops `concepts.name_ja` / `name_en` (downgrade rebuilds them from
  preferred terms).
- Seed format unchanged (`"<ja> | <en>"` pairs stay the exchange format).
- Naming (owner, 2026-11-10): the codebase says **concept** everywhere -
  packages, modules, functions, tables, API. "Tag" is only the word on
  screen (translations).

## Acceptance criteria

- [ ] No code reads `name_ja`/`name_en`; migration up/down verified.
- [ ] Seed round-trip tests and [55] tests pass unchanged.

## Dependencies

- Blocked by: [58]; the migration only after [54] (production has the
  tag tables).
