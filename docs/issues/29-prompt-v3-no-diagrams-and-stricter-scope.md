---
title: "[29] Prompts v3/r2: discourage Mermaid diagrams and tighten the scope criterion"
labels: [prompt, ai-review, data-quality, backend]
milestone: M4 Partial automation and regression safety
priority: P2
---

**Priority:** P2  **Milestone:** M4 — Partial automation and regression safety

## Summary

Align the answer prompt and the reviewer rubric with what the teacher's
review history actually shows: every Mermaid diagram in a reviewed answer
was removed as useless, and chemistry / materials / curriculum-meta
questions were rejected as out of scope - but both prompts currently
permit diagrams and only loosely bound the subject.

## Motivation

First real run of the golden eval (2026-10-30, 69 cases, 57 of them from
production reviews): exact agreement 60.9 %, publish/withhold agreement
85.5 %, reject precision 80 %, reject recall 30.8 %. Two systematic
disagreement patterns, both prompt-policy mismatches rather than
reviewer noise:

1. All 8 teacher edits whose only substantive change was removing a
   Mermaid diagram were graded APPROVE by the reviewer. The answer prompt
   says "図解が有効な場合はMermaid形式のコードブロックを使っても構いません"
   and the rubric does not mention diagrams, so the reviewer has no reason
   to flag them.
2. Teacher rejects of 放射性廃棄物処理, 金属の腐食, 衣料材料, 物質の科学,
   and 「物理」vs「物理基礎」were graded EDIT or APPROVE. The rubric's
   `scope` criterion asks "is this high-school physics" but the model treats
   physics-adjacent chemistry and course-structure questions as in scope.

## Scope

- Answer prompt (`answer` family -> v3, both languages): replace the
  Mermaid permission with "do not include diagrams; explain in words and
  formulas" (the admin UI can still render Mermaid in hand-written
  content). Add explicit out-of-scope examples: chemistry (reactions,
  materials), biology, earth science, questions about the course or exam
  rather than physics content.
- Reviewer rubric (`ai_review` family -> r2, both languages): a diagram
  present in the answer counts against `formatting`/`clarity` and warrants
  EDIT with reason FORMATTING; scope 0 and verdict REJECT with OFF_TOPIC
  for the subjects above, with the examples listed.
- Re-run `eval_prompts` and pin `baseline-v3-r2.json`; keep `v2-r1` for
  comparison. Expect reject recall and exact agreement to rise on the
  production-derived cases without lowering APPROVE agreement.
- Backfill: run `review_pending --scope stale` so existing verdicts move to
  r2 before [15]'s numbers are read.

## Acceptance criteria

- [ ] Golden eval: every `p-edit-*` Mermaid-removal case grades EDIT with
      FORMATTING; `p-reject-1070/1229/1235/1242` grade REJECT.
- [ ] No regression on `p-approve-*` beyond the tolerance.
- [ ] Fingerprints and versions bumped; `tests/test_prompts.py` updated.

## Out of scope

- The 7 teacher-approved answers the reviewer flagged as PHYSICS_ERROR -
  those need a teacher's judgement first (see eval run notes); if the
  teacher agrees with the AI, fix the content, not the prompt.

## Dependencies

- Blocked by: none
- Blocks: [18] (auto-reject needs the scope criterion to be reliable)

## Definition of done

- [ ] Backend checks pass; eval run output attached to the issue
- [ ] `docs/development.md` prompt-eval section notes the version change
