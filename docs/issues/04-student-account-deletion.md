---
title: Let a signed-in student delete their own account
labels: [feature, privacy, backend, frontend]
milestone: M0 Deploy Google Sign-In
priority: P1
---

**Priority:** P1  **Milestone:** M0 — Deploy Google Sign-In

## Summary

Add `DELETE /api/v1/users/me` and a small account page so a student can
remove their Google account from the app without e-mailing anyone.

## Motivation

The privacy page (#01) promises deletion; for minors' data that promise
should be self-service. Admins already have `DELETE /users/{id}`, but
students have no UI at all once logged in.

## Scope

- `DELETE /api/v1/users/me`: deletes the current user, clears the cookie.
  Admins are refused (409 or 400) so the last admin cannot vanish; they use
  the existing admin flow.
- Rows that reference the user keep working: `question_reviews.reviewer_id`
  already `SET NULL`; once #05 adds `questions.asked_by_user_id` it must also
  be `SET NULL`.
- Rate-limit rows for `user:<id>` may stay (they expire within a day).
- Frontend: `/account` page showing e-mail, provider, and a confirm-dialog
  "Delete my account" button; link from the header when logged in.

## Acceptance criteria

- [ ] A Google user can delete themselves and is logged out.
- [ ] An admin calling the endpoint is refused.
- [ ] Review history by that user is preserved with `reviewer_id = NULL`.

## Out of scope

- Export of personal data (can be added to the same page later).

## Technical notes

`user_service.delete_user` already exists; add a thin route plus the admin
guard. Reuse `ConfirmDialog`.

## Dependencies

- Blocked by: none (coordinate the FK rule with #05)
- Blocks: none

## Definition of done

- [ ] Backend and frontend checks pass; tests for both roles
- [ ] `docs/api.md` updated; privacy page links to `/account`
