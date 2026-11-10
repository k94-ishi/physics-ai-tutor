---
title: "[65] Comments in English, one short sentence (AGENTS.md coding style)"
labels: [refactor, docs, style]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [57]

## Summary

AGENTS.md: "Comments must be one short sentence and written in English."
Measured 2026-11-10 (comment lines, excluding lint pragmas):

| Area | Japanese comment lines |
| --- | --- |
| frontend source | 155 |
| frontend tests | 1 |
| backend source | 4 |
| backend tests | 6 |

31 files in total; the most: `admin/questions/page.tsx` (21),
`QuestionSearchAndAsk.tsx` (19), `LanguageContext.tsx` (17),
`QuestionList.tsx` (15), `StickyAskBar.tsx` (10). Many of them were
written during this month's work, so the rule was not enforced.

Also: 70 of 187 backend docstrings span several lines. Those are mostly
module docstrings that record *why* a design exists (issue numbers,
owner decisions) - valuable, but in the wrong place by the rule.

## Scope

- Translate every Japanese comment to one short English sentence.
- Long explanations move out of code: the reasoning goes to the issue it
  cites (already the system of record) or to `docs/`; the code keeps one
  sentence plus the issue reference, e.g. `# Seeded levels win ([40]).`
- Docstrings: one summary sentence; keep an Args/Returns block only
  where a signature is not self-explanatory.
- Japanese stays where it is **data**, not commentary: UI strings in
  `translations.ts`, test fixtures, prompt text, regexes for 「〜とは」.
- Enforcement so it does not regress: a small test (or lint script in
  CI) that fails on CJK characters inside comments, with an allow-list
  for data files.

## Acceptance criteria

- [ ] The check reports zero Japanese comments; it runs in CI.
- [ ] No behaviour change (comments only); all checks pass.

## Notes

Do it file by file alongside [59]-[64] when a file is touched anyway,
and sweep the rest in one PR at the end; the check lands first with the
current offenders allow-listed, shrinking to zero.

## Log

### 2026-11-11 - part 1 done: no Japanese comments

- 81 Japanese comment blocks (frontend 80 lines of files, backend tests 1)
  replaced by one short English sentence each, keeping the issue number
  so the full reasoning stays findable in the issue.
- 11 comments still contain Japanese characters on purpose: English
  sentences quoting Japanese as data (`位相 = phase`, `概念A`, `」 and と`).
- Guards in both CI jobs: `backend/tests/test_comment_style.py` and
  `frontend/src/lib/__tests__/commentStyle.test.ts` fail when Japanese is a
  fifth or more of a comment (quoted text ignored; translation tables are
  data). Each was verified by planting a Japanese comment.
- Found and fixed while doing it: the [63] hook split had left 3 comment
  groups (8 lines) in `useAdminQueueActions.ts` away from the code they
  describe (`fromUrl`, `queryState`, the similarity input and two URL
  effects, which moved to `useAdminQueueList.ts`). They now sit above
  their own code. Cause: the split script treated a comment line as a
  statement of its own.
- Checks: pytest 531, ruff, mypy, lint, tsc, vitest 176, build.

### Part 2 - waiting for the owner

The one-sentence rule is not met by 213 English items: 97 comments and
116 docstrings of more than one line (50 of them cite an issue). Many
record *why* (owner decisions, race conditions, CommonMark rules). Options
are in the 2026-11-11 report; the check does not enforce this part yet.
