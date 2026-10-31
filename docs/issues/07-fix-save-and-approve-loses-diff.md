---
title: "Bug: Save and approve records no correction diff in question_reviews"
labels: [bug, review, data-quality, frontend]
milestone: M2 Review data foundation
priority: P1
---

**Priority:** P1  **Milestone:** M2 — Review data foundation

## What happened

In `frontend/src/app/admin/questions/[id]/edit/page.tsx`, "Save and approve"
calls `PUT /questions/{id}` and then `POST /questions/{id}/review` with
`action: "APPROVE"`. The review row is created *after* the edit, so
`before_*` equals `after_*` and the action says `APPROVE`. The teacher's
correction, the most valuable signal for an AI reviewer, is not in the
history. The backend's `EDIT_APPROVE` action (which captures the diff) is
never used by the UI.

## What should have happened

One request: `POST /questions/{id}/review` with `action: "EDIT_APPROVE"`,
`language`, `question`, `answer`, so the row holds the original and the
corrected text.

## Steps to reproduce

1. Open an unreviewed AI question, change one word in the answer.
2. Click "Save and approve".
3. `GET /questions/{id}/reviews` → one row, `APPROVE`, before == after.

## Fix

- Edit page: when the text changed, send `EDIT_APPROVE` with the edited
  texts in the edited language; when nothing changed, send `APPROVE`.
- Plain "Save" without approving keeps using `PUT`.
- Backfill is impossible for existing rows; note the cutoff date in
  `docs/database.md` so later analysis excludes them.

## Definition of done

- [ ] Vitest for the edit page's request shape
- [ ] Backend test already covers `EDIT_APPROVE`; add one asserting
      `before != after`
- [ ] `docs/api.md` review section mentions which action the UI sends
