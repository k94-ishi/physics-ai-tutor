---
title: "[38] Related questions should offer prerequisites, not only similar questions"
labels: [feature, frontend, backend, recommendation]
milestone: M1 Student value
priority: P1
---

**Priority:** P1  **Milestone:** M1 — Student value

## Summary

[37] accepts advanced answers on the grounds that a student can follow
the related-QA links down to the prerequisites. Today's related list
cannot play that role: `recommendation_service.get_related_questions`
ranks candidates by **similarity** only — 0.7 × question-embedding
similarity + 0.3 × concept overlap
(`services/recommendation_service.py:20-23`). The nearest neighbours of
an advanced answer are *other advanced answers*, so a student stuck on
`d\vec{v}/dt` is offered more projectile-with-drag questions, not
"微分方程式とは".

The scaffolding the product relies on therefore does not exist yet; it
is assumed.

## Motivation

Without it, accepting advanced content ([37]) leaves students at a dead
end, and the app's distinctive claim — ask anything, climb down to what
you need — is unsupported. This is the student-facing half of [37] and
should land close to it.

## Scope

- A **prerequisite** signal distinct from similarity. Cheapest first:
  - The answer's concepts are already extracted ([39] makes the maths
    ones reliable). For each concept, find the APPROVED QA that best
    *defines* it (e.g. the question text is close to "〜とは" for that
    concept, or the QA where the concept is most central) and offer those
    as "先に読むとよい質問".
  - Prefer candidates that are **less advanced** than the current QA. A
    cheap, explainable proxy beats a learned one: count of advanced
    markers (calculus notation, vector derivatives), concept count, or a
    stored difficulty field set at generation time.
- Ranking rule (owner, 2026-11-03), replacing the "cheap proxy" above
  now that [40] is rated: a QA's node level for placement and ranking is
  **max(question level, answer level)** per axis — in the seeded data the
  question never exceeds the answer, so in practice this is the answer
  level. A **prerequisite candidate** is an APPROVED QA whose *answer*
  level falls **between the current QA's question level and answer
  level** on the axis with the larger question-to-answer gap (76 of 144
  seed rows have such a gap on the math axis). The gap is where the
  asker stands below the answer they received, so that is where the
  "read this first" link belongs.
- UI: a separate block from 関連する質問 (a different question: "what
  should I read first?"), on the question detail page.
- Honest gaps: when no APPROVED QA defines a concept, show the concept
  without a link rather than silently dropping it; consider a one-click
  "この概念について質問する" that pre-fills the ask box.
- Known constraint to document: students only see APPROVED rows
  (`PUBLIC_HIDDEN_STATUSES`), so a prerequisite asked today is invisible
  until a teacher approves it. The nightly review ([26]) plus a teacher
  pass is the latency; that is acceptable, but the gap should be visible
  to the operator, not a mystery to the student.

## Acceptance criteria

- [ ] On an advanced QA whose answer uses a differential equation, the
      prerequisite block lists the QA that explains differential
      equations when one is APPROVED.
- [ ] The block never lists the current question, rejected rows, or rows
      more advanced than the current one.
- [ ] Concepts with no defining QA are shown as gaps, not hidden.

## Out of scope

- Auto-generating the missing prerequisite answers; a full curriculum
  graph with hand-authored ordering.

## Dependencies

- Blocked by: [39] (reliable maths concepts) for the concept-based path
- Related: [37]

## Definition of done

- [ ] Backend and frontend checks pass; tests for ranking and the gap case
- [ ] `docs/api.md` updated if a new endpoint or field appears

## Log

### 2026-11-03 - concept coverage on the 144-row local corpus (see [40] log)

- Maths-tool concepts are extracted under v5: ベクトル (34 QAs), 三角関数
  (14), 三角比 (8), 微分方程式 (2), 積分 (2), 二階微分 (1).
- Gap check for the acceptance criteria: 微分方程式 is linked to 2 QAs but
  neither *defines* it, so the prerequisite block would show it as a gap
  on the air-resistance QA. That is the honest-gap path, and it confirms
  the "concept without a defining QA" case must be first-class in the UI.
