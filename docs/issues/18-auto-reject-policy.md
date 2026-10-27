---
title: Policy: auto-reject off-topic and unsafe answers with a human audit sample
labels: [feature, ai-review, security, backend]
milestone: M4 Partial automation and regression safety
priority: P3
---

**Priority:** P3  **Milestone:** M4 — Partial automation and regression safety

## Summary

Let the AI reviewer move a question to `REJECTED` on its own when the
verdict is `REJECT` with reason `OFF_TOPIC` (or an unsafe-content reason)
above a calibrated confidence, writing a `question_reviews` row with
`reviewer_kind = 'policy'`, and keep a random sample for human audit.

## Motivation

Off-topic rejection is the lowest-risk automation: a wrong auto-reject hides
a harmless answer from the cache until a teacher restores it, while a missed
one leaves junk visible. Doing this first builds confidence in the policy
mechanism (flag, logging, audit, kill switch) before anything touches
approvals.

## Scope

- `settings.ai_review_auto_reject_enabled` (default false) and
  `ai_review_auto_reject_min_confidence` chosen from #15's calibration table
  (target: ≥ 95 % agreement in that bucket).
- Policy runs right after #13 stores its row; it writes the status change
  through `question_service.review_question` so history and side effects stay
  identical to a human reject.
- Audit: 10 % of auto-rejects are additionally queued in a "policy audit"
  filter in the admin list; a teacher confirming or reverting writes a human
  row, which #15 counts.
- Kill switch: flipping the setting off stops new actions; a CLI reverts the
  last N policy rejects if needed.
- Student view (#05): auto-rejected questions show the same neutral message
  as human rejects.

## Acceptance criteria

- [ ] With the flag on and a mocked high-confidence OFF_TOPIC verdict, the
      question becomes `REJECTED` with a `policy` review row.
- [ ] With the flag off nothing changes.
- [ ] Audit filter lists the sampled items.

## Out of scope

- Auto-approve (#19).

## Technical notes

Never let the policy act on `MANUAL` or imported questions, only on
`AI_GENERATED` / `RAG_RESULT` rows that are still `UNREVIEWED`.

## Dependencies

- Blocked by: #15 (threshold), #17 (regression check), #10 (scope rule)
- Blocks: #19

## Definition of done

- [ ] Backend checks pass
- [ ] `docs/security.md` documents the policy, flag, and audit
