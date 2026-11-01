---
title: "[43] Keep the search/ask box reachable: sticky bar at the bottom of the viewport"
labels: [feature, frontend, student]
milestone: M1 Student value
priority: P3
---

**Priority:** P3  **Milestone:** M1 — Student value

## Summary

Owner idea (2026-11-01): the search window and the buttons that run the
vector search / AI generation should be fixed to the bottom of the
viewport, so a student can ask from anywhere on a long answer page
without scrolling back - the chat-like reading position.

## Scope

- Make `AskAiBox` (already rendered on the question page) a sticky
  bottom bar on the student pages; collapsed to one input line, expanding
  on focus.
- Content must never be hidden behind it: bottom padding on the page,
  and care with the on-screen keyboard on mobile (visual viewport, not
  layout viewport).
- Do not stack it over the Toast area; move toasts up when the bar is
  open.

## Acceptance criteria

- [ ] On a long answer, the ask box is visible without scrolling, on
      desktop and a 390px viewport.
- [ ] The last line of the answer can be scrolled fully into view.

## Out of scope

- Chat history / multi-turn; admin pages.

## Definition of done

- [ ] Frontend checks pass; a vitest on the layout component where practical
