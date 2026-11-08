---
title: "[30] Review: AI reviewer flags possible physics errors in 7 teacher-approved answers"
labels: [data-quality, review]
milestone: M3 AI-assisted review (advisory)
priority: P1
---

**Priority:** P1  **Milestone:** M3 — AI-assisted review (advisory)

## Summary

In the first real golden-eval run (2026-10-30) the AI reviewer graded seven
teacher-approved production answers as EDIT with `PHYSICS_ERROR`. Several
of its rationales look correct on inspection. A teacher should check each
one; if the AI is right, fix the published answer (and the corresponding
`seed.json` entry), if not, the case stays in the golden set as a known
false positive.

## Motivation

These answers are live and `APPROVED`, so students see them. Two of the
claims are textbook-clear if true (a pendulum's acceleration at the lowest
point is not zero; being *done* work on increases a body's energy).

## The seven cases (production question ids)

| id | AI claim (abridged) | My read |
| --- | --- | --- |
| 15 | Stability angle written as tanθ = h/d; should be tanθ = d/h. | Plausible - check the geometry. |
| 26 | Moment explanation omits that only the perpendicular component counts; "distance doubled → force halved" conflates two statements. | Omission rather than error; EDIT at most. |
| 45 | Cross product written F×r (should be r×F); also uses sinθ/outer product beyond the course. | Order matters for sign; TOO_ADVANCED is also fair. |
| 54 | Claims acceleration is zero at a pendulum's lowest point and at a projectile's apex. | **Wrong as stated**: centripetal acceleration at the bottom, g at the apex. |
| 178 | Internal energy stated as depending on temperature only; diatomic case (5/2 nRT) missing. | Over-generalisation; EDIT. |
| 194 | Efficiency formula presented as general where it is the Carnot (maximum) efficiency. | Precision issue; EDIT. |
| 768 | Horizontal balance written F₁+F₂=0 ignoring direction; moment balance absent. | Omission; EDIT. |
| 848 | States that a body *being done work on* loses energy. | **Wrong as stated** (sign reversed). |

Full rationales: run `eval_prompts --verbose` or see the run notes on [17].

## Acceptance criteria

- [ ] Each row has a teacher decision: fixed / disagree (with a note).
- [ ] Fixed answers edited via the admin UI with `EDIT_APPROVE` so the
      correction lands in the review history with a reason.
- [ ] `backend/eval/golden.jsonl` updated: fixed cases keep expected
      APPROVE with the corrected text; disputed cases get a `note` saying the
      AI flags them (known false positive).
- [ ] `seed.json` refreshed from production afterwards.

## Dependencies

- Blocked by: none
- Blocks: none (but informs [29]'s rubric wording)
