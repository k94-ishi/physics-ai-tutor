---
title: "[31] Admin queue: show the question id on each card and allow searching by id"
labels: [feature, frontend, backend]
milestone: M3 AI-assisted review (advisory)
priority: P2
---

**Priority:** P2  **Milestone:** M3 — AI-assisted review (advisory)

## Summary

Every card in `/admin/questions` should display its question id, and the
keyword box (or a dedicated field) should jump to a question by id.

## Motivation

Issues, eval cases (`p-approve-54`), review-run output, and the export all
refer to questions by id, but the admin queue shows neither the id nor a
way to find one - the teacher working through [30] had to search by text.
With AI-review runs and the golden set now id-centric, this is a daily
need.

## Scope

- Card header: a small monospace `#123` badge (copy-on-click is a nice
  touch), also on the edit and review-history pages.
- Search by id: accept `#123` or `id:123` in the existing keyword input and
  route it to `GET /questions/{id}` (admin sees every status), showing the
  single card; or add an `id` query parameter to the list endpoint
  (`ids=1,2,3`) so several ids can be pasted at once. Prefer the list
  parameter: it keeps pagination and selection working and lets [28]'s
  "selected" runs be driven from an id list.
- Backend: `ids` filter on `GET /questions` (admin only; comma-separated,
  max 100), documented in `docs/api.md`.
- Deep link: `/admin/questions?ids=54,848` opens exactly those cards.

## Acceptance criteria

- [ ] Each card shows its id; the eval case id `p-approve-54` can be found
      by typing `#54`.
- [ ] `?ids=54,848` lists both and nothing else; total is 2.
- [ ] Non-admin callers get the `ids` parameter ignored (public visibility
      rules unchanged).

## Out of scope

- Full-text search changes.

## Dependencies

- Blocked by: none
- Blocks: none (helps [28], [30])

## Definition of done

- [ ] Backend and frontend checks pass; vitest for the `#id` parsing
- [ ] `docs/api.md` updated
