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
| 1 | visible motion/phenomena with named quantities in a concrete situation | relations you can draw as a graph or figure / symbolic algebra over several variables |
| 2 | invisible quantities still felt in daily life (energy, pressure, current) | functions as objects, vectors, basic probability |
| 3 | classical abstractions with no sensory handle (wave phase, fields, entropy) | calculus, beginner level differential equations, vector analysis, linear algebra |
| 4 | modern/theoretical/applied physics (relativity, quantum, statistical, analytical mechanics) more advanced than level 3 | more advanced math than level 3 |

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

## Log

### 2026-11-03 - local trial of the ratings against the updated rubric (oak worktree)

- The owner rewrote the rubric above (math: graphs and algebra are both 1,
  calculus is 3, 4 is "more advanced"; physics 4 includes applied physics).
  `concept_extraction` in `prompt_library.yaml` still carried the older
  ladder, so it was aligned with this table and bumped v4 -> v5; the
  fingerprint in `tests/test_prompts.py` is re-pinned. Nothing in
  production was rated under v4, so no re-rating is lost.
- Rated the 144 seed questions on a local stack (Docker project `oak`,
  backend :8003, frontend :3003) with the real DeepSeek prompt: 0
  failures, 780 concepts, 14 concept links per question.
- Distribution (question / answer): physics 0-3, no 4 anywhere; question
  math is 0 for 76 rows and 1 for 60; answer math reaches 3 on 9 rows.
  The air-resistance QA rates q 1/1 -> a 2/3: the gap shows mainly on
  the math axis, as intended.
- **Self-agreement of the model.** A second, independent run of the same
  prompt on the same 144 rows (the parallel `elm` stack) agrees with the
  first exactly on only 67-76 % of rows per axis, but within +-1 on
  98-99 %. So the teacher validation should use "within +-1" as the
  working measure; an exact-match rate near 70 % is the ceiling the
  model sets for itself, not a sign the teacher disagrees.

  | axis | exact | within +-1 | mean abs. difference |
  | --- | --- | --- | --- |
  | question physics | 72 % | 99 % | 0.28 |
  | question math | 71 % | 99 % | 0.30 |
  | answer physics | 67 % | 99 % | 0.35 |
  | answer math | 76 % | 98 % | 0.26 |

- Review UI for the validation gate: `/admin/manage/levels` lists every
  APPROVED row with the LLM levels, a rubric that stays pinned at the top
  while scrolling, own-rating selects (kept in the browser), per-axis
  agreement (exact, within +-1, mean offset), a blind mode, and "save as
  teacher correction" (PUT levels-only). The agreement table copies as
  Markdown for this log.
- Open question for the owner: are the question levels needed at all, or
  are the answer levels enough for [38]/[42]? See the discussion of
  2026-11-03.

### 2026-11-03 - rubric wording: math 3 says "beginner-level differential equations"

Prompt and page labels updated; still v5 (the version exists only on this
unpushed branch), fingerprint re-pinned. The 144 local ratings were made
before this wording; no re-run, the change narrows level 3 slightly and
leaves the ladder intact.
