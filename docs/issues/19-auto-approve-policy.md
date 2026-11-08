---
title: Policy: auto-approve high-confidence answers that closely match approved content
labels: [feature, ai-review, backend]
milestone: M4 Partial automation and regression safety
priority: P3
---

**Priority:** P3  **Milestone:** M4 — Partial automation and regression safety

## Summary

Allow the policy to approve an AI answer when the reviewer verdict is
`APPROVE` with high confidence **and** the answer is grounded in approved
content (RAG mode with high-similarity context, or a near-duplicate of an
approved answer), with a human audit sample and the same kill switch as #18.

## Motivation

Approvals are the costly half of the teacher's queue, but a wrong approval
puts an incorrect physics explanation in front of students, so the bar must
be higher than for rejects. Requiring grounding in already-approved content
keeps the policy close to "prefer existing verified QA" from `AGENTS.md`.

## Scope

- `settings.ai_review_auto_approve_enabled` (default false),
  `..._min_confidence`, `..._min_grounding_similarity`.
- Grounding check: at least one `retrieved_question_ids` entry whose
  similarity to the new question is above the threshold and whose status is
  `APPROVED`; or exact-match of the answer's normalised text with an approved
  answer.
- Writes an `APPROVE` row with `reviewer_kind = 'policy'`; triggers the usual
  concept extraction and translation.
- Audit sample 20 % (higher than #18); the student's page (#05) shows these
  as approved, no distinction.
- Weekly report (CLI or #06 page): policy approvals, audited count,
  reversals.

## Acceptance criteria

- [ ] Ungrounded answers are never auto-approved regardless of confidence.
- [ ] A reversal by a teacher produces a human `REJECT`/`EDIT_APPROVE` row
      and the pair counts against the policy in #15.

## Out of scope

- Auto-approving edits (`suggested_answer`); only verbatim approvals.

## Technical notes

Start with auto-approve limited to one language and to RAG-mode answers;
widen only after a month of audit data.

## Dependencies

- Blocked by: #18 (mechanism proven), #15, #17
- Blocks: none

## Definition of done

- [ ] Backend checks pass
- [ ] `docs/security.md` and `README.md` describe the human-in-the-loop guarantee
