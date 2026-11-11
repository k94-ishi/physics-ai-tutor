---
title: "[74] Latency quick wins independent of async: vector index, pool settings, compression"
labels: [performance, backend, database]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67]

## Summary

Small, independent latency items that need no async work. Each is
cheap; each is measured with the [68] timings before and after, and
dropped if it does not pay.

## Motivation

Not all latency is thread starvation. These close the gaps that async
cannot: query cost, connection setup, and bytes on the wire.

## Scope

- **pgvector index**: there is no HNSW/IVFFlat index — every similarity
  search scans all embeddings. At ~150 questions × 2 languages × 2 types
  this is negligible, so the owner decided (2026-11-11) **not** to add it
  as a separate early change: it ships here, as part of this issue.
  Alembic migration for an HNSW index (`vector_cosine_ops`, matching the
  `<=>` queries in `embedding_repository`). HNSW recall is approximate;
  verify the golden similarity expectations in the suite still hold with
  the index on.
- **Connection pool**: sizes are explicit since [69] (5 + 10 with
  `pool_pre_ping`); what remains is choosing the right numbers against
  the Supabase pooler and the worker count ([75]). [70] showed the pool
  is now the binding constraint once threads no longer are - 60
  concurrent asks took 50.5 s against a 15-connection pool - so size it
  together with [72]'s fix for connections held across LLM calls, and
  re-measure rather than assuming a bigger pool is the answer.
- **Response compression**: long markdown answers and admin lists are
  text; check what Render/Vercel already compress, and if the backend
  responses cross the wire uncompressed, add `GZipMiddleware` with a
  sane minimum size.
- Record each item's before/after in the Log; revert what does not help.

The frontend fetch audit that used to sit here moved to its own issue
([77]) once it turned out there was a real serial wave to remove.

## Acceptance criteria

- [ ] Each shipped item has a measured before/after in the Log.
- [ ] Index migration with working downgrade; similarity tests green;
      seed/reset flows unaffected.

## Out of scope

- Caching layers (Redis etc.) — no new infrastructure.
- Model or prompt changes.

## Technical notes

The index migration must also build on the test database quickly (tiny
tables — fine) and on Supabase without locking writes for long
(`CREATE INDEX CONCURRENTLY` cannot run inside a transaction; Alembic
needs `autocommit_block` for it). Production application follows the
usual rule and the track's deploy decision: the owner applies migrations
to production at the end of the track, never from a dev session.

Pool sizing interacts with [75]: if the backend ends up running several
workers, the per-process pool multiplies by the worker count against
Supabase's limit. Size them together.

## Dependencies

- Blocked by: [68] (to measure). Independent of [69]–[73]; can run any
  time alongside them.
- Related: [75] (worker count and the connection budget).

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Frontend checks pass if touched
- [ ] `docs/database.md` documents the index (if shipped);
      `docs/development.md` notes the pool settings
