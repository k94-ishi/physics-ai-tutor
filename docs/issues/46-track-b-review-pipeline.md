---
title: "[46] Track B: review pipeline and policies - resumes after [37]"
labels: [epic, roadmap, ai-review]
milestone: M4 Partial automation and regression safety
priority: P2
---

**Priority:** P2  **Milestone:** M4 — Partial automation and regression safety

Ordered queue; details live in each issue. Deliberately paused until
[37] `e00868e` lands: a policy trained on "self-contained or edit" data
would suppress the advanced answers the app exists for.

1. [16] `e106e6c` few-shot grounding from past human reviews
2. [20] `274f94c` versioned prompt rollouts with A/B comparison
3. [18] `70a4933` auto-reject policy (gate: >=95% agreement in the acting bucket)
4. [19] `e6ad07e` auto-approve policy (after 3. proves the mechanism)
