---
title: Student question history tied to the review loop
labels: [feature, backend, frontend, review]
milestone: M1 Student value
priority: P1
---

**Priority:** P1  **Milestone:** M1 — Student value

## Summary

Remember which signed-in student asked each question, and give them a "My
questions" page that shows the current (possibly teacher-corrected) answer
and its review status.

## Motivation

Today a student's AI answer is lost to them once the tab closes, and they
never learn that a teacher later fixed or rejected it. This is the feature
that makes logging in worthwhile beyond a larger quota, and it closes the
pedagogical loop that the review workflow exists for.

## Scope

- Migration: `question_asks` table (`id`, `question_id` FK CASCADE,
  `user_id` FK SET NULL, `language`, `created_at`) rather than a single
  column, so cache hits by other students are recorded too and one question
  can have many askers. Index on (`user_id`, `created_at`).
- `POST /ai/ask` records an ask row for signed-in callers on both cache hit
  and cache miss (anonymous asks are not recorded).
- `GET /api/v1/users/me/questions`: paginated, newest first, returns the
  question in the student's language with `status` and `provenance`.
- Frontend `/me/questions` page; header link when logged in; status badge
  (unreviewed / approved / rejected) reusing the existing labels.
- Rejected questions: show the question and a neutral "this answer was
  withdrawn by a teacher" message, not the rejected answer text.

## Acceptance criteria

- [ ] Asking twice (one miss, one hit) yields two rows for the same user.
- [ ] After an admin EDIT_APPROVE, the student's page shows the corrected
      answer and the approved badge.
- [ ] Anonymous asks create no rows; another user cannot see my rows.

## Out of scope

- Notifications when a review happens (would need e-mail or push).
- Teacher view of "what my class asked" (#06 covers aggregate counts).

## Technical notes

Visibility rule in `docs/security.md` still applies: non-admins must not see
`UNREVIEWED` content *of others*; seeing one's own unreviewed answer is the
existing cache behaviour and is fine, keep the "not yet reviewed" label.

## Dependencies

- Blocked by: none
- Blocks: #06 (distinct-student counts), #14 (asker count as review priority)

## Definition of done

- [ ] Backend and frontend checks pass; migration downgrade verified
- [ ] `docs/api.md`, `docs/database.md` updated
