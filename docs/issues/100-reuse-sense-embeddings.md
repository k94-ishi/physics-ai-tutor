---
title: "[100] Reuse sense embeddings instead of re-embedding every candidate on each extraction"
labels: [backend, performance, cost]
milestone: M1 Student value
priority: P3
---

**Priority:** P3  **Milestone:** M1 — Student value  **Track:** [67]

## Summary

When an extracted tag pair shares a word with existing senses, concept
matching embeds the new pair **and every candidate sense's words** to
compare them, on every extraction. Each sense already stores a vector
(`concepts.embedding`). Reuse it, or cache by text, so a sense is not
embedded again each time it is a candidate.

## Motivation

Owner's question (2026-11-13): are the meaning embeddings skipped once
they have been computed? They are not. Checked in
`concept_service._resolve_sense` / `_async_resolve_sense`:

- both words already on exactly one sense: no embedding call (fine);
- otherwise: one OpenAI request with the pair plus each candidate's
  `"<ja> | <en>"` text, every time;
- a new sense does reuse the pair vector computed for the comparison.

Common words (速度, 位相, "phase") are candidates again and again, so the
same texts are embedded repeatedly: wasted cost and latency, not wrong
results.

## Scope

**Decision (owner, 2026-11-13): a migration is acceptable.** Both
options discussed keep vectors in the database; they differ in the key.
A vector keyed by the sense goes stale on a rename; a vector keyed by
the text cannot. The plan takes the best of both:

- **Keep the vector on the sense** (`concepts.embedding`) and add one
  column, `concepts.embedding_text_hash`: SHA-256 of the model and the
  exact `"<ja> | <en>"` text the vector was made from (same scheme as
  `embedding_service.vector_key`).
- Matching uses the stored vector when the hash equals the hash of the
  sense's current text, and re-embeds only the senses whose hash
  differs, saving the new vector and hash in the same short write.
- Why not a separate text-keyed table: `recommendation_service`
  (`average_concept_similarity`) also reads `concepts.embedding` to rank
  related questions. A cache table would leave that column stale after a
  rename; fixing the column itself fixes both readers.
- Migration: add the nullable column; existing rows start NULL, which
  counts as "unknown" and is re-embedded the first time the sense is a
  candidate (or by an optional one-off backfill CLI). Downgrade drops
  the column.
- New senses store the hash at creation; the editor rename ([90]) does
  not call OpenAI - the mismatch is caught lazily at the next match.
- Keep the matching rule shared ([91]) and the offline seed at zero
  OpenAI calls (the seed file carries the vectors; write the hash too).

## Acceptance criteria

- [ ] A second extraction meeting the same candidate senses makes no
      embedding request for them (asserted by counting mock calls).
- [ ] Sense matching decisions unchanged on the existing tests
      (`test_concept_senses.py`), including the homonym and synonym cases.
- [ ] Measured: embedding calls per extraction before and after.

## Out of scope

- Tuning `CONCEPT_SENSE_MATCH_THRESHOLD` ([80]: that needs eval data).

## Dependencies

- Best after [95], when only the async matching path is left, so the
  change is made once.
- Related: [76] (batch embeddings on import), [49] (the query cache).

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Migration with verified downgrade
- [ ] `docs/database.md` documents the column

## Log

### 2026-11-13 — plan chosen

Owner asked where the vector lives (the database, in both options) and
accepted a migration. Chosen: vector on the sense plus a text hash, for
the reason under Scope: the related-questions ranking reads the same
column, so a separate cache would leave it stale.
