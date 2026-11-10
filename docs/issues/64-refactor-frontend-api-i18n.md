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

## Log

### 2026-11-11 - done

- `lib/api.ts` (586 lines, 43 functions + `ApiError`) -> `lib/api/`:
  `client.ts` (URLs, `apiFetch`, `ApiError`, `jsonInit`), `questions.ts`
  (16), `concepts.ts` (9), `users.ts` (6), `admin.ts` (6), `auth.ts` (5),
  `ai.ts` (1), and `index.ts` re-exporting them. The 26 import sites and the
  15 `vi.mock("@/lib/api")` tests are unchanged: no API function calls
  another, so mocking the index still covers every call.
- `translations.ts` (1,196 lines, 499 keys) -> `lib/i18n/translations/`:
  common 60, student 44, account 53, admin 163, adminStats 68, levels 75,
  conceptsAdmin 36, grouped by key prefix (some prefixes were scattered
  over the old file). Each file types `en` against its own `ja`, so a
  missing English key fails `tsc` in that file.
- Proof of no change: the same 44 exports and every function body found
  verbatim; a temporary test showed the merged table equals the old one
  value for value in both languages (then removed).
- Guard: `importBoundary.test.ts` (verified by planting a direct import).
- Checks: lint, tsc, vitest 174, build.
