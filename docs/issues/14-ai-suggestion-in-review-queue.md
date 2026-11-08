---
title: Show the AI pre-review in the admin queue and sort by it
labels: [feature, ai-review, review, frontend, backend]
milestone: M3 AI-assisted review (advisory)
priority: P2
---

**Priority:** P2  **Milestone:** M3 — AI-assisted review (advisory)

## Summary

Surface each unreviewed question's latest AI verdict, confidence, and
reasons in `/admin/questions`, let teachers sort and filter by it, and
pre-fill the review dialog with the AI's reason and suggested edit.

## Motivation

The advisory stage only pays off if it saves teacher time: likely-reject
items can be handled first, likely-approve items can be batch-checked, and
the suggested edit turns a rewrite into a diff review. It also produces the
human verdicts that #15 compares against.

## Scope

- `QuestionResponse` (admin only) gains `ai_review: {verdict, confidence,
  reasons, rationale, suggested_answer, created_at} | null`.
- List endpoint: `sort=ai_confidence|asked_count|oldest`, filter
  `ai_verdict=APPROVE|EDIT|REJECT|NONE`.
- Queue row: a compact badge (verdict + confidence) and the top reason;
  expandable rationale.
- Review dialog (#08): reason preselected from the AI's first reason;
  "Apply suggested answer" button that loads `suggested_answer` into the
  edit form, clearly marked as AI-suggested until the teacher saves.
- Asked-count sort uses #05's rows when present.

## Acceptance criteria

- [ ] Sorting by confidence orders rows as the API says; filter hides others.
- [ ] Applying a suggestion then approving produces an `EDIT_APPROVE` row
      whose `before` is the original AI answer.

## Out of scope

- Any automatic status change.

## Technical notes

One extra left join on the latest `ai_reviews` row per question; keep it in
the repository layer.

## Dependencies

- Blocked by: #08, #13
- Blocks: #15 (needs human verdicts on AI-reviewed items)

## Definition of done

- [ ] Backend and frontend checks pass
- [ ] `docs/api.md` updated
