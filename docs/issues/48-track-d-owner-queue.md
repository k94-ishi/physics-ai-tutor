---
title: "[48] Track D: owner's queue - console, judgement, and go-aheads"
labels: [epic, roadmap, ops]
milestone: M3 AI-assisted review (advisory)
priority: P1
---

**Priority:** P1  **Milestone:** M3 — AI-assisted review (advisory)

Steps only the owner can do. Nothing in Tracks A-C waits on them, but
several multiply their value once done. Details live in each issue or in
docs/operator-checklist.md.

1. [26] `e0594f1` add the two GitHub secrets; confirm the first scheduled run
2. Verify [27] `0d50e7e` and [28] `c03d036` in the admin UI; close when satisfied
3. Production rollout 7f3b1c9d4e21 -> a1b2c3d4e5f6 (backup first; checklist Phase 2)
4. Go-ahead for the [37] eval re-run (~70 DeepSeek calls)
5. [40] `785a7e9` validation: rate ~30 questions and compare with the model's levels
6. [44] `fd0b3e9` re-verdict on p-edit-250 and p-edit-4 (TOO_ADVANCED labels predate the policy)
7. [30] `4ef75f5` close when nothing further is wanted
