---
title: "[39] Concept extraction must reliably capture the mathematical tools an answer leans on"
labels: [prompt, data-quality, backend]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value

## Summary

Concepts are the link targets that make [37]'s scaffolding and [38]'s
prerequisite block work. The v3 instruction says *"extract the **physics**
concepts"*, while the worked example extracts ベクトル, 単位, $m/s^2$ —
so mathematical tools are included in practice but not by the rule. For
an answer built on `m \frac{d\vec{v}}{dt} = m\vec{g} - k\vec{v}`, the
concepts that matter most to a stuck student are 微分方程式 and
ベクトルの微分, and nothing in the prompt guarantees they appear.

## Motivation

A prerequisite that is never extracted can never be linked, so the
student meets the ODE with no way down. This is a small prompt change
with an outsized effect on whether [37] is safe to ship.

## Scope

- `concept_extraction` prompt: say explicitly that the mathematical
  tools and notation an answer relies on are concepts too (微分方程式,
  ベクトルの微分, 指数関数, 三角比 …), alongside the physics concepts.
- Extend the ja and en worked examples with one such case so the format
  is demonstrated, not just described.
- Bump `concept_extraction` v3 → v4 and re-pin the fingerprint.
- Measure before/after on a handful of advanced production answers: do
  the maths concepts now appear? Cheap to check with the existing CLI.

## Acceptance criteria

- [ ] An answer containing a differential equation yields 微分方程式 (or
      the equivalent) as an extracted concept in both languages.
- [ ] Ordinary answers do not gain noise concepts (spot-check ~10 rows
      before and after).

## Out of scope

- Re-extracting the whole corpus; schedule that as a one-off run after
  the prompt settles.

## Dependencies

- Blocks: [38]

## Definition of done

- [ ] Backend checks pass; `tests/test_prompts.py` fingerprint updated
- [ ] Before/after comparison recorded in this issue
