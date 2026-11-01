---
title: "[42] Question-page layout: more related questions, floating preview, and a two-axis grid"
labels: [feature, frontend, student, design]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value

## Summary

Three owner ideas (2026-11-01) about the student question page, bundled
because they reshape the same screen:

1. **More than five related questions.** The page hardcodes
   `fetchRelatedQuestions(id, 5, …)` while the API already allows 20.
   Raise the default and add a "もっと見る" expansion.
2. **Floating preview.** Opening a related QA currently navigates away;
   a modal (floating window) that previews the QA keeps the student's
   place while they peek at a prerequisite — exactly the [38] climbing
   motion. Reuse `MarkdownContent`; link through to the full page from
   the modal.
3. **Two-axis grid.** Once [40] gives every QA `physics_level` ×
   `math_level`, arrange the related questions on those two axes instead
   of a flat list: the current question sits at its own coordinates,
   prerequisites appear down-and-left, extensions up-and-right. This is
   the visual form of "the graph is the scaffolding" - and it is only
   meaningful *with* two axes; without [40] a grid is decoration.

Plus a bounded visual pass: consistent spacing/colour hierarchy on the
student pages (status colours already exist; apply them consistently),
not an open-ended redesign.

## Scope

- Related list: default 10, expand to 20; keep order from the API.
- `QuestionPreviewModal` shared component (used from related list, the
  [38] prerequisite block, and [41]'s concept lists later).
- Grid view behind the data being present: rows = math level, columns =
  physics level (or transposed after trying both); QAs without levels
  fall back to the list. Mobile falls back to the list.
- Visual pass limited to the question detail and search/ask pages.

## Acceptance criteria

- [ ] 10+ related questions visible with expansion to the API maximum.
- [ ] A related QA opens in a preview modal without losing the page;
      the modal links to the full page.
- [ ] With levels present, the grid places the current question at its
      coordinates and at least one item lower on an axis when one exists.

## Out of scope

- The prerequisite *ranking* itself ([38]); per-student personalisation.

## Dependencies

- Grid blocked by: [40]. Items 1-2 blocked by nothing.
- Related: [38], [41]

## Definition of done

- [ ] Frontend checks pass; vitest for the modal and the grid fallback
