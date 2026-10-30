---
title: "[28] Admin UI: AI-review selected questions and re-review a single one"
labels: [feature, ai-review, frontend, backend]
milestone: M3 AI-assisted review (advisory)
priority: P2
---

**Priority:** P2  **Milestone:** M3 — AI-assisted review (advisory)

## Summary

In `/admin/questions`, add a bulk action **AI review** for the selected
rows and a per-card **Re-review with AI** button, both running as a
`scope=selected` run from [25] with per-card progress badges like concept
extraction.

## Motivation

A teacher triaging the queue wants a verdict on *these* questions now - for
example the ones just asked, or ones whose verdict looks wrong after a
prompt change - without reviewing the whole backlog.

## Scope

- Bulk action in the existing selection bar: confirm dialog with the count
  (and a note when some selected rows are not AI-generated or not
  unreviewed - those are skipped and reported).
- Per-card button on unreviewed AI rows: **Re-review** (replaces nothing;
  a new `ai_reviews` row becomes the latest, so the badge updates).
- Progress: reuse the per-card processing/done/failed badge pattern from
  concept extraction, driven by polling the run.
- Respects the daily cap and the overlap guard; shows the API's 409 as a
  "run in progress" toast.

## Acceptance criteria

- [ ] Selecting 2 unreviewed AI questions and 1 manual question and
      running the action reviews exactly the 2 and reports 1 skipped.
- [ ] Re-review on a card produces a new latest verdict reflected in the
      badge without reloading the page.

## Out of scope

- Reviewing APPROVED/REJECTED rows (the reviewer is for the pending queue).

## Dependencies

- Blocked by: [25]
- Blocks: none

## Definition of done

- [ ] Frontend and backend checks pass
- [ ] `docs/api.md` updated
