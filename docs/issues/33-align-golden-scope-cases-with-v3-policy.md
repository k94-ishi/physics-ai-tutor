---
title: "[33] Separate the subject and level axes in the v3/r2 prompts; realign the golden scope cases"
labels: [eval, ai-review, prompt]
milestone: M4 Partial automation and regression safety
priority: P2
---

**Priority:** P2  **Milestone:** M4 — Partial automation and regression safety

## Summary

[29] `84ff079` closed with the owner's decision to broaden the reviewer's
scope criterion from "high-school physics" to "physics" and keep Mermaid
permitted. The golden set still expects REJECT on the cases that decision
re-admits — p-reject-1229 and p-reject-1235 (chemistry/materials),
p-reject-1070 (nuclear-waste policy), p-reject-47 and p-reject-201
(course-structure) — so the pinned v3/r2 baseline carries reject recall
23.1 % as a permanent floor. An eval that permanently disagrees with
documented policy masks real regressions and blocks the ≥ 95 % agreement
gate that [18] `70a4933` and [19] `e6ad07e` depend on.

Separately, g05 (English homework, not physics under any scope) now grades
APPROVE — a true miss, not a policy consequence — and
`compare_with_baseline` (`backend/physics_ai_tutor/cli/eval_prompts.py:154`)
gates only exact agreement and reject precision, so the recall collapse
would never have failed CI.

## Scope

- Teacher decides per re-admitted case: relabel (REJECT → APPROVE or EDIT
  with the correct reasons, updating the note with date and rationale), or
  keep the label and re-tighten the rubric's scope criterion instead. The
  two goals conflict; the eval cannot decide it (see [29]'s discussion).
- Keep g05 as REJECT regardless — it is the canary for [18]'s OFF_TOPIC
  auto-reject and currently fails.
- Extend `compare_with_baseline` to also gate `publish_agreement_rate` and
  `reject_recall` (recall is the metric [18] acts on), with tolerances that
  respect the measured ±3-verdict run noise.
- Re-run and re-pin after relabelling.

## Acceptance criteria

- [ ] Every golden case's expected verdict matches the teacher's current
      policy, with a dated note on each changed case.
- [ ] A reject-recall drop > tolerance fails `eval_prompts` with exit 1.

## Dependencies

- Blocked by: [32] (reconcile the lost relabels first)
- Blocks: [18] `70a4933`

## Definition of done

- [ ] Backend checks pass; baseline re-pinned; `eval/README.md` updated
