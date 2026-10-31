---
title: "[25] AI review runs: job records, overlap guard, trigger endpoint, stale re-review"
labels: [feature, ai-review, backend]
milestone: M3 AI-assisted review (advisory)
priority: P2
---

**Priority:** P2  **Milestone:** M3 — AI-assisted review (advisory)

## Summary

Turn the `review_pending` CLI into a proper run: an `ai_review_runs` record
per invocation (who/what started it, scope, counts, token usage, status), a
guard so two runs cannot overlap, a service entry point that the scheduler
([26]) and the admin UI ([27], [28]) share, and a "stale" mode that
re-reviews questions whose latest verdict came from an older reviewer
prompt version.

## Motivation

Today the only way to review the backlog is the CLI on a shell. Scheduled
and admin-triggered runs both need the same things the CLI lacks: a record
of what ran and what it cost, protection against concurrent runs burning
the budget twice, progress visible to the person who pressed the button,
and a way to refresh verdicts after the rubric prompt changes (otherwise
`review_pending` never revisits a question that already has any review).

## Scope

- Migration: `ai_review_runs` (`id`, `trigger` = `scheduled` / `manual` /
  `cli`, `started_by_user_id` nullable FK SET NULL, `scope` = `pending` /
  `stale` / `selected`, `requested_count`, `reviewed_count`,
  `failed_count`, `prompt_tokens`, `completion_tokens`, `status` =
  `running` / `done` / `failed` / `cancelled`, `started_at`, `finished_at`,
  `error` text nullable).
- `ai_review_service.run(db, scope, question_ids=None, limit, trigger,
  started_by)`: creates the run row, iterates with the existing
  `review_question`, updates counts as it goes (so progress can be polled),
  marks done/failed. Honours a per-run `limit` and a daily cap
  (`settings.ai_review_daily_cap`, default e.g. 200) measured over
  `ai_reviews.created_at` in the last 24h.
- Overlap guard: refuse to start when a run is `running` and younger than
  a timeout (Postgres advisory lock or a unique partial index on
  `status='running'`); runs older than the timeout are marked `failed`.
- Stale scope: UNREVIEWED AI questions whose latest `ai_reviews.prompt_version`
  != `REVIEW_PROMPT_VERSION`.
- `review_pending` CLI becomes a thin wrapper over `run(...)` with
  `--scope pending|stale` and records `trigger=cli`.
- Admin endpoints: `POST /admin/ai-review/runs` (body: scope, limit,
  question_ids) returning the run; `GET /admin/ai-review/runs` (recent
  runs) and `GET /admin/ai-review/runs/{id}` for polling. The POST runs
  the job in a FastAPI background task and returns immediately.
- Cost preview: `GET /admin/ai-review/pending-count?scope=` returning how
  many questions a run would touch and the remaining daily cap.

## Acceptance criteria

- [ ] Starting a second run while one is `running` returns 409 and creates
      no row.
- [ ] A run over 3 pending questions ends `done` with `reviewed_count=3`,
      token totals summed from the three `ai_reviews` rows.
- [ ] A reviewer failure on one question increments `failed_count` and does
      not stop the run.
- [ ] Stale scope picks a question reviewed under `r0` but not one under
      the current version.
- [ ] The daily cap is enforced across runs.

## Out of scope

- Any UI (that is [27]/[28]) and the scheduler itself ([26]).

## Technical notes

Background work inside the web process is acceptable at this scale (one
instance, tens of questions); if runs grow long, [26]'s external scheduler
is the right home. Per-question failures already never raise
(`review_question` returns None) - count them.

## Dependencies

- Blocked by: none ([13] shipped)
- Blocks: [26], [27], [28]

## Definition of done

- [ ] Backend checks pass; migration downgrade verified
- [ ] `docs/api.md`, `docs/database.md`, `docs/security.md` (cost note) updated
