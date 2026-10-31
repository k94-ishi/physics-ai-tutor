---
title: "[35] Bug: review response drops the AI verdict; small admin-UI defects in the AI-review surfaces"
labels: [bug, ai-review, frontend, backend]
milestone: M3 AI-assisted review (advisory)
priority: P2
---

**Priority:** P2  **Milestone:** M3 — AI-assisted review (advisory)

## What happened

1. **The AI badge vanishes from a card after reviewing it.**
   `frontend/src/app/admin/questions/page.tsx:366-368` replaces the list
   row with the `POST /questions/{id}/review` response, but that endpoint
   (`backend/physics_ai_tutor/api/v1/questions.py:412-449` →
   `services/question_service.py:568`) calls only `prepare_for_response`
   and never `attach_ai_reviews` / `attach_generation_meta`, unlike the
   list and detail endpoints. Approving or rejecting a card under the
   "all"/APPROVED filter silently drops its verdict badge, rationale, and
   the pre-selected reject reason, although the `ai_reviews` row exists.
2. **Stale "suggestion applied (unsaved)" state on the edit page.**
   `frontend/src/app/admin/questions/[id]/edit/page.tsx:93,302-309`:
   `suggestionApplied` is set once and never reset. Applying the
   suggestion and then clicking "Translate missing" reloads `texts` from
   the server, discarding the suggestion, yet the badge still claims it is
   applied and the Apply button stays disabled (:382).
3. **Null confidence rendered as "0 %".** Edit page :363 uses
   `Math.round((aiReview.confidence ?? 0) * 100)`; the queue badge
   (page.tsx:946-950) correctly hides it when `confidence === null`. An
   unparsed verdict should not display as zero confidence.
4. **Unvalidated URL-to-union casts.** `page.tsx:126-127` casts
   `queryState.sort` and `queryState.aiVerdict` straight from the URL into
   the union types; `?sort=garbage` reaches the API and surfaces as a
   generic fetch error instead of being dropped.

## What should have happened

The review response carries the same admin enrichments as the list and
detail endpoints; UI state derived from server data resets when that data
reloads; null confidence is hidden; URL params are validated before use.

## Scope

- Backend: attach AI reviews and generation metadata to the review
  response for admins (one place: the review endpoint's response path).
- Frontend: reset `suggestionApplied` whenever `loadQuestion` replaces the
  texts; hide confidence when null on the edit page; validate `sort` /
  `aiVerdict` (and the pre-existing `status`) against the allowed values
  when reading the URL.

## Acceptance criteria

- [ ] Reviewing a card in the queue keeps its AI badge (vitest + backend
      test on the response shape).
- [ ] After "Translate missing", the Apply button is enabled again and the
      stale badge is gone.
- [ ] `?sort=garbage` lists with the default sort instead of erroring.

## Definition of done

- [ ] Backend and frontend checks pass; regression tests added
