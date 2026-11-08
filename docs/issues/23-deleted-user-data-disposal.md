---
title: "[23] Dispose deleted users' residual data (purge rate-limit rows; UUID tombstone for reviewer history)"
labels: [privacy, backend, feature]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value

## Summary

Finish the deletion story from [04]: purge the ex-user's `rate_limit_hits`
rows at deletion, and replace a deleted reviewer's identity in
`question_reviews` with a per-user random UUID tombstone instead of plain
NULL. Student ask history keeps `SET NULL` deliberately.

## Motivation

After [04]/[05], deleting an account removes the `users` row and nulls the
foreign keys, but two residues remain:

- `rate_limit_hits` rows keyed `user:<id>` survive up to ~1 day after the
  account is gone - the only place the deleted numeric id still appears.
- `question_reviews.reviewer_id` goes NULL, which destroys the audit
  grouping ("these 30 reviews were by the same teacher") that the review
  workflow and [11]/[15] analyses want.

## Considered: a random UUID for *all* deleted-user references

Replacing every reference (including `question_asks.user_id`) with one
random UUID per deleted user was considered and rejected for student data:
a stable pseudonym keeps all of a student's questions linkable to one
person, and a set of questions can itself identify a minor. That is
pseudonymisation, not disposal, and the privacy page promises that deleting
the account "removes the link". `SET NULL` (current behaviour) collapses
all deleted users together and is the stronger guarantee - keep it.

For *reviewers* the trade-off flips: they are staff, not minors; the value
of the trail is accountability and reviewer-level analysis ([11] already
plans a pseudonymous reviewer hash for exports); and the texts involved are
reviews, not personal questions. A random UUID written once at deletion,
with the mapping stored nowhere, preserves grouping without identity.

## Scope

- Migration: `question_reviews.reviewer_tombstone` (uuid, nullable, no FK).
- `user_service.delete_user`: in the same transaction, (1) assign one fresh
  `uuid4` to `reviewer_tombstone` on all of the user's review rows, then let
  `reviewer_id` go NULL via the FK; (2) delete `rate_limit_hits` rows whose
  `bucket_key = 'user:<id>'` (both `ai_ask` and any future per-user actions).
- Expose `reviewer_tombstone` only in admin review responses; [11]'s export
  uses it as the `reviewer_kind`-adjacent stable id for deleted reviewers.
- `question_asks`: no change (`SET NULL` stays); state the reasoning in
  `docs/security.md`'s deletion section and keep the privacy page wording.

## Acceptance criteria

- [ ] Deleting a user leaves zero `rate_limit_hits` rows for `user:<id>`.
- [ ] Two reviews by the same deleted reviewer share one tombstone; reviews
      by different deleted reviewers have different tombstones.
- [ ] The tombstone appears in `GET /questions/{id}/reviews` (admin only).
- [ ] `question_asks.user_id` is still NULL after deletion (unchanged).

## Out of scope

- Retroactively tombstoning reviewers deleted before this ships (their
  rows are already NULL; nothing to group by).
- Any change to student ask history.

## Dependencies

- Blocked by: none
- Blocks: refines [11] (export field) and [15] (per-reviewer grouping)

## Definition of done

- [ ] Backend checks pass; migration downgrade verified
- [ ] `docs/database.md`, `docs/security.md`, `docs/api.md` updated
