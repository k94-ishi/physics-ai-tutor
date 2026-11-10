---
title: "[63] Frontend: shared hooks and cards; split the admin queue page"
labels: [refactor, frontend]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [57]

## Summary

`admin/questions/page.tsx` is 1,398 lines with 21 `useState`; the
request-id race guard is hand-copied in 5 components; the preview card
markup in 2. AGENTS.md asks for reusable components.

## Scope

- `useLatestRequest()` hook (request id + loading/error) replacing the 5 copies.
- `QuestionCard` (preview button + tags + optional badges) used by the
  home list, related list, "Read these first" and similarity results.
- Split the admin queue into `AdminQueueFilters`, `AdminQuestionCard`,
  `BulkActionBar`, `useAdminQueue` (state + loading), keeping the URL
  state contract (`useQueryState`) unchanged.
- Same treatment, lighter, for `edit/page.tsx` (570) and
  `manage/levels/page.tsx` (581) if time allows.
- Consider moving student components to `components/questions/` and
  keeping `components/ui/` for generic pieces only.

## Acceptance criteria

- [ ] No page/component file over ~400 lines.
- [ ] Existing vitest suites pass without changing their assertions
      (only imports may change).

## Dependencies

- Blocked by: none (independent of the backend steps)
