---
title: "[56] Open the preview modal from the home page (cards and similarity results)"
labels: [feature, frontend, student]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value

## Summary

Owner's original request (2026-11-07): the "Questions" tab on the home
page should open the same floating preview the question page uses, so a
student keeps their place in the list. Split out of [42] on 2026-11-10,
when [42] closed with everything else done.

## Scope

- Home-page cards and similarity results open `QuestionPreviewModal`;
  the modal's "open full page" button navigates.
- Cards now also hold tag links ([41]), so the card's main link becomes
  the preview trigger and the tags stay separate links (never nested).
- Similarity results carry `SimilarQuestion` (no tags, no levels): the
  modal accepts that shape instead of fetching more.
- Unchanged: the exact-match redirect and the RAG answer card.

## Acceptance criteria

- [ ] A home-page card and a similarity result open the preview without
      leaving the page; the modal links to the full page.
- [ ] Tag links on a card still go to the tag's list.

## Definition of done

- [ ] Frontend checks pass; vitest for both entry points
