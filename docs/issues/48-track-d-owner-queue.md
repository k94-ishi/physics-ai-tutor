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
3. Production rollout: backup, migrate to head (now includes d1e2f3a4b5c6),
   deploy (checklist Phase 2). Then `backfill_levels` (5.3a) and the
   production sample of [52].
4. ~~Go-ahead for the [37] eval re-run~~ done: ran with [51], baseline
   v5-r5 pinned 2026-11-03
5. ~~[52] local difficulty validation~~ done 2026-11-04, decision GO;
   the production sample remains (after 3.)
6. [44] `fd0b3e9` re-verdict on p-edit-250 and p-edit-4 (owner confirmed
   2026-11-03 they stay edits; redo them through 保存して承認 so the
   history carries the diff and reason)
7. [30] `4ef75f5` close when nothing further is wanted
