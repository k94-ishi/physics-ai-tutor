---
title: "[64] Frontend: split api.ts and translations.ts by feature"
labels: [refactor, frontend, i18n]
milestone: M1 Student value
priority: P3
---

**Priority:** P3  **Milestone:** M1 — Student value  **Track:** [57]

## Summary

`lib/api.ts` (586 lines, 42 functions) and `lib/i18n/translations.ts`
(1,196 lines) grow with every feature and conflict in parallel work.

## Scope

- `lib/api/` with `client.ts` (`apiFetch`, `ApiError`, URL builders) and
  one file per area: `questions.ts`, `concepts.ts`, `auth.ts`, `users.ts`,
  `admin.ts`, `ai.ts`; `lib/api/index.ts` re-exports so imports and the
  `vi.mock("@/lib/api")` tests keep working.
- Translations split by namespace (`common`, `questions`, `tags`,
  `admin`, ...) and merged into the same typed table; the existing
  "identical keys in ja and en" test keeps guarding it.

## Acceptance criteria

- [ ] Public import paths unchanged; all checks pass.

## Dependencies

- Best after [63] (fewer moving imports)
