---
title: "[37] Accept advanced content the question genuinely needs; the related-QA graph is the scaffolding, not inline derivation"
labels: [prompt, ai-review, eval, data-quality]
milestone: M3 AI-assisted review (advisory)
priority: P1
---

**Priority:** P1  **Milestone:** M3 — AI-assisted review (advisory)

## Summary

The v4/r3 `level` axis asks every answer to be self-contained: *"define
the concepts and symbols you introduce and build the explanation in an
order a high school student can follow; never assume prior knowledge."*
The owner's model of the product is different and, on reflection, better
suited to it: an answer may **rely on prerequisites it does not teach**,
because every QA shows its related QAs, so a student who meets
`m \frac{d\vec{v}}{dt} = m\vec{g} - k\vec{v}` can follow a link to
"微分方程式とは" or "ベクトルの微分とスカラーの微分の違い". Serving a
student who reaches for advanced physics is a main point of the app, and
the knowledge graph — not the single answer — carries the scaffolding.

Concrete case (owner, 2026-11-01): *"How is projectile motion treated
when there is air resistance?"* answered with the vector ODE above.
**This should be APPROVED.**

## Motivation

Under today's rubric that answer is a likely EDIT: the `level` criterion
deducts for "calculus introduced without explaining the notation", and
`TOO_ADVANCED` exists as a reason code. Each such edit teaches the
dataset that correct, necessary advanced physics is a defect, which is
the opposite of the product's intent and will later drive [18]/[19] to
suppress exactly the answers the app exists to give.

## The distinction to encode

Necessity, not difficulty:

| Case | Verdict | Why |
| --- | --- | --- |
| Air resistance answered with a vector ODE | APPROVE | The honest treatment needs it; no high-school method gives the result |
| `g10`: v-t graph slope answered with $\lim_{\Delta t \to 0}$ and 導関数 | EDIT (`TOO_ADVANCED`) | A basic question dressed in calculus the student did not need |

So `TOO_ADVANCED` keeps a real meaning: **advanced machinery the question
did not call for**, not "advanced".

## Scope

- Answer prompt (ja + en), `level` section: allow necessary advanced
  content; require that the concepts it leans on are **named explicitly**
  (so they are searchable and linkable) rather than fully derived inline;
  a one-line gloss is enough. Keep "prefer the high-school method when
  the topic allows it", which is what keeps `g10` an EDIT.
- Reviewer rubric (ja + en), `level` criterion: score 2 when the advanced
  content is necessary and its prerequisites are named; deduct when the
  machinery was unnecessary for the question, or when it appears
  unnamed/unexplained so a student cannot even look it up. Restate
  `TOO_ADVANCED` accordingly.
- Check the answer length targets (1000 chars / 400 words) still fit an
  advanced answer that must name its prerequisites; raise only if the
  eval shows truncation.
- Golden set: add at least two APPROVE cases of *necessary* advanced
  content (the air-resistance ODE; one more, e.g. 単振動 with
  $\ddot{x} = -\omega^2 x$), and keep `g10` as EDIT so the pair pins the
  distinction rather than a blanket "advanced is fine".
- Version bump (answer v5, rubric r4), re-pin `baseline-v5-r4.json`.

## Acceptance criteria

- [ ] The air-resistance ODE answer grades APPROVE; `g10` still grades
      EDIT with `TOO_ADVANCED`.
- [ ] Reject recall and publish agreement do not regress beyond the
      gate's tolerance.

## Out of scope

- Changing what is *in scope* by subject ([33] settled that).
- Generating the prerequisite QAs themselves ([38]).

## Dependencies

- Blocked by: none
- Blocks: [18], [19] (a policy must not suppress necessary advanced
  answers), and should land before much more review data accumulates
  under the current wording.

## Definition of done

- [ ] Backend checks pass; fingerprints re-pinned
- [ ] Eval re-run and baseline committed (~70 DeepSeek calls)
- [ ] `docs/operator-checklist.md` 1.1 describes the necessity rule
