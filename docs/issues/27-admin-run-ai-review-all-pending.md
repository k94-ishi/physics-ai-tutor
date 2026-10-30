---
title: "[27] Admin UI: start an AI review run for all pending questions"
labels: [feature, ai-review, frontend, backend]
milestone: M3 AI-assisted review (advisory)
priority: P2
---

**Priority:** P2  **Milestone:** M3 — AI-assisted review (advisory)

## Summary

A button on `/admin/stats` (next to the agreement section) that starts an
AI review run over every pending question, shows the cost preview before
confirming, and shows progress and recent runs afterwards.

## Motivation

Teachers should not need a shell to get verdicts for today's queue, and the
person pressing the button should see how many calls it will make and
whether a run is already going.

## Scope

- Panel "AI review runs": pending count and stale count (from [25]'s
  preview endpoint), remaining daily cap, a **Review all pending** button
  (and **Re-review stale** when stale > 0) behind a confirm dialog that
  states the number of DeepSeek calls.
- After confirming: poll `GET /admin/ai-review/runs/{id}` every few seconds
  and show reviewed/failed/requested with a progress bar until `done`; then
  refresh the queue counts and the agreement section.
- Recent runs table: started, trigger, scope, counts, tokens, status, who.
- Disable the buttons (with the reason) while a run is `running` or the
  cap is exhausted.

## Acceptance criteria

- [ ] With 3 pending questions the dialog says 3 calls; after confirming,
      progress reaches 3/3 and the queue shows the new badges.
- [ ] A second click during a run shows the running state instead of
      starting another run (409 from the API handled gracefully).

## Out of scope

- Picking individual questions ([28]).

## Technical notes

Reuse the `Toast`/`ConfirmDialog` components; i18n ja+en.

## Dependencies

- Blocked by: [25]
- Blocks: none

## Definition of done

- [ ] Frontend checks pass; vitest for the preview/confirm/progress flow
- [ ] `docs/api.md` lists the endpoints the UI uses
