---
title: Measure AI-reviewer agreement with human reviews
labels: [feature, ai-review, observability, backend, frontend]
milestone: M3 AI-assisted review (advisory)
priority: P2
---

**Priority:** P2  **Milestone:** M3 — AI-assisted review (advisory)

## Summary

For every question that has both an `ai_reviews` row and a later human
`question_reviews` row, compute agreement; report it per verdict, per reason
code, per prompt version, and over time, on the admin stats page and as a
CLI report.

## Motivation

This number decides whether any automation (#18, #19) is safe, and at what
confidence threshold. It also tells you whether a new answer prompt version
(#10, #20) changed quality.

## Scope

- `services/review_metrics_service.py`: confusion matrix (AI verdict ×
  human action), precision/recall for REJECT, reason-code overlap (Jaccard),
  calibration table (confidence decile → human agreement rate), all
  groupable by `prompt_version` (answer and reviewer) and by month.
- `GET /api/v1/admin/stats/review-agreement` and a section on `/admin/stats`
  (#06).
- CLI `review_metrics --since DATE` printing the same tables, usable on an
  #11 export file as well as on the DB.
- Minimum sample guard: show "n too small" under 30 pairs.

## Acceptance criteria

- [ ] On a fixture of 10 known pairs the matrix and precision/recall are
      exactly as computed by hand.
- [ ] Grouping by prompt version separates rows correctly.

## Out of scope

- Statistical significance tests; counts and rates are enough for now.

## Technical notes

Pair rule: the latest `ai_reviews` row created *before* the human review.
If the human reviewed first (backlog), exclude the pair.

## Dependencies

- Blocked by: #12, #13, #14 (to accumulate pairs), #06 (page)
- Blocks: #18, #19, #20

## Definition of done

- [ ] Backend and frontend checks pass
- [ ] `docs/development.md` describes how to read the calibration table
