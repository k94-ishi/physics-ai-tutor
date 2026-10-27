<!-- Copy this file, fill it in, then: git bug bug new -t "<title>" -F <copy>.md -->
<!-- Labels are added afterwards: git bug bug label new <id> P1 M2 feature backend -->
<!--
Keep every section; write "None" rather than deleting one.
Priority: P0 = blocks deployment, P1 = next, P2 = planned, P3 = later.
-->

**Priority:** P?  **Milestone:** M? — <name>

## Summary

One or two sentences: what changes for the user or operator.

## Motivation

Why this is worth doing now, and what happens if it is not done.

## Scope

- What is included, as concrete bullets (endpoints, pages, tables, prompts).

## Acceptance criteria

- [ ] Observable behaviour that can be checked, one per line.

## Out of scope

- What this issue deliberately leaves out (link follow-up issues).

## Technical notes

Files, layers, and constraints. Follow `AGENTS.md`: repository/service/router
separation, Alembic migration for schema changes, no production DB edits.

## Dependencies

- Blocked by: #
- Blocks: #

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Frontend: `npm run lint`, `tsc --noEmit`, `npm test`, `npm run build` pass
- [ ] Alembic migration added and downgrade verified (if schema changed)
- [ ] `docs/` updated (`api.md`, `database.md`, `security.md`, or `development.md` as relevant)
- [ ] Reviewable by a human: educational content changes are visible in the admin UI
