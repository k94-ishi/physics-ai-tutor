---
title: Structured review reasons on reject and edit
labels: [feature, review, data-quality, backend, frontend]
milestone: M2 Review data foundation
priority: P1
---

**Priority:** P1  **Milestone:** M2 — Review data foundation

## Summary

Add a required reason code (and optional comment) when a reviewer rejects or
edits an AI answer, in both single and bulk review.

## Motivation

`question_reviews.comment` exists but the UI never sends it, so the history
says *what* changed and never *why*. An AI pre-reviewer (#13) needs labelled
failure modes to be evaluated against, and a teacher reading the queue later
benefits too. Every review done before this ships is lost labelling.

## Scope

- Migration: `question_reviews.reason` (`varchar`, nullable for `APPROVE`).
  Codes, kept short and physics-specific:
  `PHYSICS_ERROR`, `MATH_ERROR`, `INCOMPLETE`, `OFF_TOPIC`, `TOO_ADVANCED`,
  `UNCLEAR`, `FORMATTING`, `LANGUAGE`, `DUPLICATE`, `OTHER` (comment required).
- Schema validation: `REJECT` and `EDIT_APPROVE` require `reason`; `OTHER`
  requires `comment`.
- Admin UI: a small dialog on reject / edit-approve / bulk reject with a
  select and a comment box; bulk approve stays one click.
- Review history page shows reason and comment.

## Acceptance criteria

- [ ] API rejects `REJECT` without a reason (422).
- [ ] Bulk reject applies the same reason to all selected rows.
- [ ] Reason appears in `GET /questions/{id}/reviews`.

## Out of scope

- Changing the codes later is fine; store strings, not an enum type in SQL.

## Technical notes

Keep `QuestionReviewAction` as is; add `QuestionReviewReason` StrEnum in
`schemas/question_review.py`. Export in #11 must include the field.

## Dependencies

- Blocked by: #07 (same UI surface; land together or in order)
- Blocks: #11, #13, #15

## Definition of done

- [ ] Backend and frontend checks pass; migration downgrade verified
- [ ] `docs/api.md`, `docs/database.md` updated
