---
title: "[40] Two-axis difficulty per QA (physics, math), assigned during concept extraction"
labels: [feature, backend, prompt, data-quality]
milestone: M1 Student value
priority: P1
---

**Priority:** P1  **Milestone:** M1 — Student value

## Summary

Give every question two difficulty levels per axis, 0-4, rated by the
**nature of the content itself**, not a school curriculum (owner's
policy, 2026-11-01: curricula change and do not translate; abstraction
does):

| level | physics (distance from direct experience) | math (nature of the tool) |
| --- | --- | --- |
| 0 | everyday phenomena anyone can see and feel | everyday arithmetic |
| 1 | visible motion/phenomena with named quantities in a concrete situation | relations you can draw as a graph or figure |
| 2 | invisible quantities still felt in daily life (energy, pressure, current) | symbolic algebra over several variables |
| 3 | classical abstractions with no sensory handle (wave phase, fields, entropy) | functions as objects, vectors, basic probability |
| 4 | modern/theoretical physics (relativity, quantum, statistical, analytical mechanics) | calculus, differential equations, vector analysis, linear algebra |

The owner reviews this rubric once ratings exist; the wording is a first
draft and deliberately not precious.

Assigned by the LLM **in the same call as concept extraction** (one
prompt, no extra API cost), stored on `questions`, editable by the
teacher in the admin UI because an LLM estimate is advisory.

## Motivation

This is the owner's tutor framing (2026-11-01) made measurable: *the
question signals the student's level* — air resistance with drag is an
advanced asker, the slope of a v-t graph is a beginner. One "difficulty"
number cannot say "easy physics, hard math" (a kinematics question that
needs calculus) or the reverse; two axes can. Downstream it is the
missing ingredient for:

- [38]: "prerequisite" = related QA with lower difficulty on the axis
  the student is stuck on — a principled direction instead of a regex
  proxy for calculus notation.
- [42]: the two-dimensional related-QA grid needs two dimensions.
- [37]: the necessity rule becomes checkable (an answer far above its
  question's level is suspect; a hard question with a hard answer is
  expected).

## Scope

- Migration: `physics_level`, `math_level` (small ints, nullable =
  not yet rated) on `questions`.
- Concept-extraction prompt: emit two final lines
  (`physics_level: N` / `math_level: N`) after the concept lines; parse
  them; bump the family version and fingerprint **together with [39]**
  so the family is bumped once, not twice.
- Record levels at generation time for new questions; a backfill pass
  over existing rows reuses the stale re-extraction machinery (one-off
  CLI run, cap-aware).
- Admin UI: show both levels on the card and make them editable on the
  edit page; teacher corrections overwrite the LLM value.
- Expose both levels in the public question payload for [41]/[42].

## Acceptance criteria

- [ ] A new question gets both levels in the same LLM call as concepts.
- [ ] The air-resistance ODE case rates physics 3 / math 3; the v-t
      slope question rates physics 1 / math ≤ 1 (snapshot test with a
      mocked LLM; real values are the teacher's to correct).
- [ ] An admin can change either level and the change sticks.

## Out of scope

- Using the levels for ranking or display (that is [38]/[42]).
- Per-student level profiles.

## Dependencies

- Do together with: [39] (same prompt family, one version bump)
- Blocks: [42]'s grid; strengthens [38]

## Definition of done

- [ ] Backend checks pass; Alembic migration; docs/api.md updated
- [ ] Backfill CLI documented in the operator checklist
