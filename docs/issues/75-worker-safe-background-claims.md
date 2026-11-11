---
title: "[75] Worker-safe background claims: move de-duplication into the database, then scale out"
labels: [backend, performance, correctness, async]
milestone: M1 Student value
priority: P1
---

**Priority:** P1  **Milestone:** M1 — Student value  **Track:** [67]

## Summary

Background translation de-duplicates work with an in-process set and a
thread lock, so it only holds inside one process. Move the claim into
the database (as the AI review run guard already does), then run more
than one uvicorn worker. This is what unlocks the cheapest latency fix
available: more workers.

## Motivation

Found by a coworker's review (2026-11-11) and confirmed:
`background_translation_service` keeps `_in_flight` / `_concepts_in_flight`
as module-level sets behind a `threading.Lock`. With two workers, each
has its own copy, so the same question can be claimed and translated
twice — two DeepSeek calls, two writes racing on the same row, for one
row's worth of value.

Today the system runs a single uvicorn process (`docker-compose.yml`,
`backend/Dockerfile`, no `--workers`), so the bug is latent. But adding
workers is the most direct way to raise throughput, and after [70]–[73]
it is the obvious next move — so the claim has to be correct *first*,
or scaling out quietly doubles the LLM bill.

Note the contrast: AI review runs already guard correctly with a partial
unique index on `status='running'` plus per-item transactions ([25],
[34]). That is the pattern to copy.

## Scope

- Replace the in-memory claim with a database-backed one. Simplest
  option that fits the existing schema: claim by a conditional `UPDATE`
  on the question row (e.g. a `translation_claimed_at` column, claimed
  only when NULL or older than a timeout), so exactly one worker wins
  and a crashed claim expires. A `SELECT ... FOR UPDATE SKIP LOCKED`
  claim over the queued ids is the alternative; pick one and write down
  why in the Log.
- Same for concept-name translation claims (`_concepts_in_flight`).
- Keep every current guarantee: approved-only re-check, at most one
  DeepSeek call per row, a translated row never re-queued, and the task
  body still never raises.
- Alembic migration for whatever column the claim needs, with a
  verified downgrade.
- A test that two concurrent claimers (two sessions) produce exactly one
  translation — the test that the in-memory version cannot pass.
- Only then: run multiple workers. Add `--workers` (or Render's
  equivalent) as a documented setting, measure with the [68] probe, and
  record how many workers the Supabase connection limit allows given the
  pool settings from [74].

## Acceptance criteria

- [ ] No module-level mutable claim state and no `threading` primitives
      in services.
- [ ] Two sessions claiming the same question: one translates, the other
      skips — covered by a test.
- [ ] A worker that dies mid-translation does not block the row forever
      (claim expires, next view retries).
- [ ] Multi-worker run measured against single-worker in the Log, with
      the connection budget written down.

## Out of scope

- An external job queue or a separate worker process (no new
  infrastructure). This keeps background work in the web processes.
- The AI review run guard, which is already database-backed.

## Technical notes

The claim must be committed to be visible to other workers, so it is its
own small transaction before the work starts, released in a `finally`.
Watch the interaction with [72]'s in-process concurrency limit: the
semaphore bounds one worker, the database claim bounds all of them —
both are needed, for different reasons. Workers also multiply the
DeepSeek request rate, so re-check the concurrency defaults from [72]
after scaling out.

## Dependencies

- Blocked by: [72] (which converts these bodies to asyncio); may be done
  right after it. Correctness part can land before any scaling out.
- Blocks: running more than one worker, anywhere.

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Alembic migration added and downgrade verified
- [ ] `docs/database.md` documents the claim column;
      `docs/development.md` documents the worker count and why the claim
      must be database-backed
