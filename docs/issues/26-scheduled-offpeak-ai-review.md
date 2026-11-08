---
title: "[26] Scheduled AI review runs in DeepSeek's off-peak window"
labels: [feature, ai-review, ops, backend]
milestone: M3 AI-assisted review (advisory)
priority: P2
---

**Priority:** P2  **Milestone:** M3 — AI-assisted review (advisory)

## Summary

Run the pending (and stale) AI review automatically once a day inside
DeepSeek's discounted off-peak window instead of reviewing inline at
generation time.

## Motivation

The review is advisory and latency-free, so it should run when tokens are
cheapest. DeepSeek has no Batch API (verified against the live endpoint on
2026-10-30: `/batches` returns 404 while `/models` and `/files` exist), but
it discounts the window UTC 16:30-00:30 (JST 01:30-09:30). Context caching
already makes the long rubric prefix cheap on repeated calls, which a dense
nightly run maximises. With a scheduler in place, `AI_REVIEW_ENABLED` can
stay off in production and teachers still find verdicts in the morning.

## Scope

- Pick the runner and document the choice (recommendation first):
  1. **GitHub Actions `schedule`** calling the CLI with production
     secrets - no new infrastructure, logs in Actions, cron in UTC, but
     needs the DB reachable from Actions (Supabase pooler is).
  2. Render Cron Job running `review_pending` in the backend image - closest
     to the app, costs a small monthly fee.
  3. In-process scheduler (APScheduler) - no new service, but ties the job
     to web-process uptime and restarts; avoid unless 1 and 2 fail.
- The job calls `ai_review_service.run(scope="pending")` then
  `scope="stale"` with `trigger="scheduled"`, bounded by the daily cap from
  [25]; the window is a setting (`AI_REVIEW_OFFPEAK_START/END`, UTC) so the
  CLI refuses to start outside it unless `--force`.
- Alerting: a failed run or a run that hit the cap shows on the stats page
  via `ai_review_runs`; optionally a GitHub Actions failure e-mail.
- Document pricing assumptions in `docs/development.md` with the date
  checked, since DeepSeek changes them.

## Acceptance criteria

- [ ] A scheduled run appears in `ai_review_runs` with `trigger=scheduled`.
- [ ] Running the CLI outside the window without `--force` exits with a
      clear message and reviews nothing.
- [ ] Two consecutive scheduled runs do not overlap (guard from [25]).

## Out of scope

- Batch API integration (not offered by DeepSeek); revisit if the reviewer
  moves to a provider that has one.

## Dependencies

- Blocked by: [25]
- Blocks: none

## Definition of done

- [ ] Workflow/cron definition committed; secrets documented, not committed
- [ ] `docs/development.md` deployment section updated
