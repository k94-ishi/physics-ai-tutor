---
title: "[44] Teacher re-verdict: the old TOO_ADVANCED edits predate the advanced-content policy"
labels: [eval, data-quality, ai-review]
milestone: M4 Partial automation and regression safety
priority: P3
---

**Priority:** P3  **Milestone:** M4 — Partial automation and regression safety

(Filed in git-bug as `fd0b3e9` on 2026-11-01 by a parallel session; copied
here on 2026-11-02 when issue management moved to files.)

## Summary

Two production edits in the golden set removed advanced content under the
old "stay within the course" policy. Since 2026-11-01 the policy is the
opposite — advanced physics is accepted and the QA graph carries the
prerequisites ([33], [37]) — so these labels may now teach the AI
reviewer yesterday's rule. Same shape as the scope-case review in [33],
but on the level axis. Only the teacher can re-judge them.

| case | what the 2026-08 edit did | question for the teacher |
| --- | --- | --- |
| `p-edit-250` (音の屈折) | removed $v = \sqrt{\gamma R T}$ as "beyond the course" | under the new policy, would you now keep the formula (named and explained)? If yes, the EDIT/TOO_ADVANCED label is stale. |
| `p-edit-4` (平面内の運動) | removed $dx/dt$ notation from a basic "what is planar motion" answer | probably still a fair edit — the *question* is basic and the notation was gratuitous — but confirm. |

Not in question: `g10` stays EDIT/TOO_ADVANCED by construction (a basic
v-t-graph question answered *only* in calculus with no plain reading is a
level defect under the new policy too, which defines TOO_ADVANCED as
machinery the question never needed).

## Scope

- Teacher records a verdict per case (a dated Log entry here is enough).
- If a label changes: update `golden.jsonl` (note with date and
  rationale), re-run `eval_prompts`, re-pin the baseline. Two cases move
  recall/precision by one verdict each, so expect the numbers to shift.
- The v5/r4 length allowance for advanced questions ([37]) already
  addressed the companion note about the 1000字 / 400-word target.

## Acceptance criteria

- [ ] Both cases carry a dated teacher verdict.
- [ ] Baseline re-pinned if any label changed.

## Dependencies

- Blocked by: none (teacher judgement only). Listed in Track D ([48]).

## Definition of done

- [ ] Backend checks pass; `eval/README.md` notes the decision
