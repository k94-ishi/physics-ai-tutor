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
