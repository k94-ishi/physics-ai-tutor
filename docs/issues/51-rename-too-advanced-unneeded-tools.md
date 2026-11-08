---
title: "[51] Rename TOO_ADVANCED to UNNEEDED_TOOLS; g10 becomes APPROVE (rubric r5)"
labels: [ai-review, prompt, eval, frontend, backend]
milestone: M3 AI-assisted review (advisory)
priority: P2
---

**Priority:** P2  **Milestone:** M3 — AI-assisted review (advisory)

## Summary

`TOO_ADVANCED` no longer names what it means. Since [33]/[37] the code
has meant "machinery the question clearly never needed, or a concept
used without a name the student cannot look up" — never "the topic is
advanced". The owner (2026-11-03) decided to keep that criterion but
rename the code, and to keep it deliberately separate from the [40]
difficulty axes: the axes measure content, the code marks a review
defect.

## Decisions encoded here (owner, 2026-11-03)

- New code: **UNNEEDED_TOOLS**. Old rows keep `TOO_ADVANCED` in the
  database; it stays in the backend enum and in the translations (marked
  legacy) so history renders, but it is no longer offered as a choice.
- **g10 flips to APPROVE.** The v-t-graph wording does not prove the
  asker is a beginner; a student who finds calculus too hard re-asks
  ("もっとやさしく") or follows the related questions. The rubric's
  level criterion drops the v-t example, deducts only for *clearly*
  unneeded machinery, and says to let doubtful cases pass.
- The [44] cases (p-edit-250, p-edit-4) stay edits; [44] is a teacher
  re-verdict task, not blocked by this rename.

## Scope

- `ai_review` prompts ja+en: rename the code, "clearly", the
  doubt-passes rule; bump r4 -> r5, re-pin the fingerprint.
- `QuestionReviewReason`: add UNNEEDED_TOOLS, keep TOO_ADVANCED as
  legacy. Frontend choices swap to the new code; `ReviewReason` type
  keeps the legacy member for stored rows.
- Golden set: g10 APPROVE with no reasons; re-pin `baseline-v5-r5.json`
  after the eval run (~70 DeepSeek calls, owner approved 2026-11-03).

## Acceptance criteria

- [ ] New reviews can only pick UNNEEDED_TOOLS; an old TOO_ADVANCED row
      still shows a readable label in the review history.
- [ ] Eval gate passes against the re-pinned baseline; g10 counted as
      APPROVE.

## Dependencies

- Related: [37], [40], [44]

## Log

### 2026-11-03 - implemented; eval run and baseline pinned

One run of the 68-case set under answer v5 / rubric r5 (real DeepSeek):

| metric | r4 baseline | r5 |
| --- | --- | --- |
| exact agreement | 72.1 % | 70.6 % |
| publish agreement | 94.1 % | 95.6 % |
| reject precision | 87.5 % | 87.5 % |
| reject recall | 77.8 % | 77.8 % |

The 1.5-point exact drop is within the ~3-verdicts-of-68 run-to-run
noise. The cases this issue is about behave: g10 grades APPROVE,
p-edit-4 and p-edit-250 still grade EDIT (the model cites
PHYSICS_ERROR/INCOMPLETE rather than the tools code - they are flawed
answers, not merely over-tooled ones). p-reject-201 stays the known
miss ([33] log). `baseline-v5-r5.json` pinned.
