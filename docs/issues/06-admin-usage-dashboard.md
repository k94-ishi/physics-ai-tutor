---
title: Admin usage dashboard from rate_limit_hits and question_asks
labels: [feature, observability, backend, frontend]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value

## Summary

An admin page with a handful of counters: generations per day, cache-hit
ratio, distinct signed-in students, anonymous 429s, and the review backlog.

## Motivation

The limits (3/h anonymous, 10/h signed in) were chosen without data. The
limiter already records every generation by bucket, so a few `GROUP BY`
queries tell you whether a school NAT is hitting the anonymous limit, how
much caching saves, and how fast the unreviewed queue grows.

## Scope

- `GET /api/v1/admin/stats?days=14` (admin only) returning per-day:
  `generations`, `cache_hits` (needs #05's ask rows, else omit), `distinct_users`,
  `unique_ip_buckets`, `rate_limited` (count of 429s; add a cheap log-free
  counter or derive from hits at the cap), plus totals: unreviewed count,
  median age of unreviewed questions.
- Frontend `/admin/stats` with a simple table; no chart library.

## Acceptance criteria

- [ ] Numbers match a hand-run SQL query on the test database.
- [ ] Page loads in under a second with a year of hits (index exists).

## Out of scope

- Per-student drill-down (privacy; aggregate only).

## Technical notes

Repository functions over `RateLimitHit` and `QuestionAsk`; keep SQL in the
repository layer. Pruning keeps `rate_limit_hits` to one day, so for longer
history either stop pruning `ai_ask` rows or add a nightly rollup table —
decide here and document it.

## Dependencies

- Blocked by: #05 for cache-hit and student counts (can ship without them)
- Blocks: #15 (agreement metrics can live on the same page)

## Definition of done

- [ ] Backend and frontend checks pass
- [ ] `docs/api.md` updated
