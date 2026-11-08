---
title: Versioned prompt rollouts with A/B comparison
labels: [feature, prompt, ai-review, backend]
milestone: M4 Partial automation and regression safety
priority: P3
---

**Priority:** P3  **Milestone:** M4 — Partial automation and regression safety

## Summary

Allow two answer-prompt versions to run side by side on a percentage split,
record the version on each row (#09), and compare teacher outcomes and AI
reviewer agreement per version (#15) before promoting one.

## Motivation

By this point every prompt change has an offline check (#17), but offline
sets drift from what students actually ask. A small live split closes the
loop with real questions while the human review stays the ground truth.

## Scope

- `core/prompts.py` holds `ANSWER_PROMPTS: dict[version, text]` per
  language; `settings.answer_prompt_rollout = {"v2": 90, "v3": 10}`.
- Assignment per question (hash of question text + day) so the same
  question gets the same version within the cache window.
- #15 and #06 group by `prompt_version` already; add a "promote" note in
  `docs/development.md`: when to flip the default and remove the old text.

## Acceptance criteria

- [ ] With a 50/50 split, rows are assigned both versions and each row's
      `prompt_version` matches the prompt actually used.
- [ ] The stats page shows per-version approve/edit/reject rates.

## Out of scope

- Model A/B (different providers); same mechanism could be reused later.

## Technical notes

Cache lookup is by question text, so a cached answer may come from the other
version; that is acceptable and visible in the row.

## Dependencies

- Blocked by: #09, #15, #17
- Blocks: none

## Definition of done

- [ ] Backend checks pass
- [ ] `docs/development.md` updated
