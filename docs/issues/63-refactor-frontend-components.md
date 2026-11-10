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

## Log

### 2026-11-11 - done

| File | Before | After |
| --- | --- | --- |
| `app/admin/questions/page.tsx` | 1,398 lines, 21 `useState` | 423 (layout and dialogs) |
| `useAdminQueueList.ts` (new) | - | 283: URL filters, loading, keyword/id input, similarity search, paging |
| `useAdminQueueActions.ts` (new) | - | 407: selection, approve/reject, bulk, extraction, AI review runs, delete |
| `components/admin/AdminQuestionCard.tsx` (new) | - | 349 |
| `components/admin/AdminQueueFilters.tsx` (new) | - | 235 |

- **Moved, not rewritten**: the card and filter JSX and every statement of
  the two hooks were moved verbatim by scripts; only closure references
  became props (card: 11 values -> 14 props; filters: 12 values -> 13
  props). The URL-state contract (`useQueryState`) is unchanged.
- `useLatestRequest()` replaces 7 hand-copied request counters in 5 files
  (`begin()` -> `isCurrent()`, `cancel()`); the returned object is stable,
  so adding it to hook dependency lists recreates nothing.
- `QuestionCard` replaces the three identical student cards (home list,
  related questions, "Read these first"); only the hover tone differed.
- Tests: the admin queue page had 2 tests and none for the card's actions,
  so `AdminQuestionCard.test.tsx` (4) pins them **before** further moves;
  `useLatestRequest.test.tsx` (3). Every existing suite passes with its
  assertions unchanged. lint, tsc, vitest 173, build: pass.
- Pre-existing quirk found and kept (no behaviour change in a refactor):
  clicking a tag chip on an admin card also toggles the card's selection,
  because the chip is outside the click-stopping action row. Harmless (the
  filter change clears the selection), pinned in the card test; fix it in a
  feature change if wanted.

Not done (optional in the scope): `admin/questions/[id]/edit/page.tsx`
(570) and `admin/manage/levels/page.tsx` (581) are still over 400 lines;
moving student components into `components/questions/`.

### 2026-11-11 - correction found in [65]

The hook split left 3 comment groups in `useAdminQueueActions.ts` away from their code (the code itself was correct). Fixed in [65]; see its log.
