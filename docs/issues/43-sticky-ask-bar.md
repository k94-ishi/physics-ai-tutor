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

## Log

- **2026-11-02** Implemented on the **question detail page** in commit
  (see below). `StickyAskBar` fixes `AskAiBox` to the bottom, measures
  its own height with a ResizeObserver, and uses that height twice: an
  in-flow spacer so the end of an answer is never hidden, and a
  `--ask-bar-height` CSS variable that `Toaster` offsets by, so toasts
  sit above the bar instead of under it. Height is capped at `70svh`
  with internal scrolling, `env(safe-area-inset-bottom)` keeps it clear
  of the iOS home indicator, and the root layout now sets
  `interactiveWidget: "resizes-content"` so the soft keyboard pushes the
  page instead of covering the bar.
- **Not done, deliberately: the home page.** There the search component
  *wraps the question list as its children* (the list is its pre-search
  fallback), so making it sticky would pin the whole list to the bottom.
  Restructuring that is real work and is not what this issue asked for;
  on the home page the search box is already the first thing on screen.
  If a sticky bar is wanted there too, it needs
  `QuestionSearchAndAsk` split into "the form" and "the results" first -
  worth its own issue.
- The bar did not need the planned collapse-on-blur: the component only
  renders results after a search, so its resting height already is one
  input line.
