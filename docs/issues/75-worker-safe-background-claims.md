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

- [x] No module-level mutable claim state and no `threading` primitives
      in services; both enforced by `tests/test_architecture.py`.
- [x] Two sessions claiming the same question: one translates, the other
      skips — covered by tests, including eight separate OS processes.
- [x] A worker that dies mid-translation does not block the row forever
      (claim expires, next view retries).
- [x] Multi-worker run measured against single-worker in the Log, with
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

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] Alembic migration added and downgrade verified
- [x] `docs/database.md` documents the claim table;
      `docs/development.md` documents the worker count and why the claim
      must be database-backed

## Log

### 2026-11-12 — done

598 tests pass (was 588); ruff and mypy clean.

**A table, not a column.** The issue suggested a
`translation_claimed_at` column on `questions`, with another on
`concepts` for the name claims. I used a dedicated `background_claims`
table of `(kind, key, claimed_at)` with a unique `(kind, key)` instead,
because it is *one* mechanism rather than two parallel ones, it keeps
operational bookkeeping out of the content tables, and the next kind of
claim costs a constant rather than another migration. The cost is a
small extra table and one indexed lookup per item, which is nothing
beside the LLM call it guards. No foreign key to `questions` or
`concepts` on purpose: deleting content should not have to care whether
a claim happens to exist.

The claim is a single statement, so the decision is the database's and
not a read followed by a write that another worker can interleave with:

```sql
INSERT INTO background_claims (kind, key, claimed_at) VALUES (...)
ON CONFLICT ON CONSTRAINT uq_background_claims_work
DO UPDATE SET claimed_at = now()
      WHERE background_claims.claimed_at < now() - interval '15 minutes'
RETURNING id
```

A live claim matches no row and returns nothing, so the caller knows it
lost. An expired one is taken over, which is what keeps a crashed worker
from parking a row forever. `SELECT ... FOR UPDATE SKIP LOCKED` was the
alternative; it needs the row to exist first and holds a lock for the
duration, which is exactly the "connection waiting on an LLM" shape
[82] just removed.

**The claim moved into the task.** It used to be taken by the router,
which then decided whether to queue anything. Now the router queues
unconditionally and each item claims for itself, so the holder is
whoever actually does the work — correct no matter which process queued
it, and the release lives in the same `finally` as the work.

**Proof it works across processes.** Eight separate OS processes raced
for one key: exactly one won, seven lost, one row in the table. That is
the test the in-memory set could not pass — it would have reported eight
winners. The suite has the same shape with eight concurrent sessions,
plus expiry, non-expiry of a fresh claim, release on success, release on
failure, and a row held by another worker not being translated.

**Workers, measured** (local, 200-row database, 800 requests to
`/questions?size=50` at concurrency 32):

| Workers | p50 | p95 | Wall | Throughput | Connections |
| --- | --- | --- | --- | --- | --- |
| 1 | 99 ms | 166 ms | 2.7 s | ~296 req/s | 6 |
| 2 | 72 ms | 122 ms | 1.9 s | ~421 req/s | 11 |
| 4 | 51 ms | 101 ms | 1.5 s | ~533 req/s | 21 |

Sub-linear — the database and the probe become the shared limit — but
real: 1.4x at two workers, 1.8x at four. `WEB_CONCURRENCY` needs no code
change; uvicorn reads it natively.

**The connection budget, which is the real constraint.** Each worker
builds its own pools, and until [73] retires the sync engine there are
two per worker: `(5 + 10) x 2 = 30` worst case each. Two workers can
therefore demand 60 against a Supabase instance that typically allows
~60 direct, and four can demand 120. Observed usage was far lower (~5
per worker under that load), but a slower database opens more. **Two
workers is the safe ceiling today**; four becomes reasonable once [73]
halves it and [74] settles the sizing. Written into
docs/development.md rather than left in this log.

**Not done here:** actually raising `WEB_CONCURRENCY` in production.
The Render start command lives in the dashboard, and the track deploys
as one piece after every step ([67]), so this is the owner's switch to
flip — with the budget above in hand.
