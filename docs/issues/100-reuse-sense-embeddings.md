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

Pick one, and write down why:

1. **Use the stored vector.** Compare against `concepts.embedding`. It
   was computed from the sense's words at creation; a teacher may have
   renamed the sense since ([55] editor), so the stored vector can be
   stale. Either re-embed on rename (the editor then calls OpenAI), or
   accept comparing against the original meaning.
2. **Cache by text.** A small table keyed by (hash of the pair text,
   model), like `query_embeddings` ([49]). Always exact; costs a
   migration.

Either way: keep the matching rule shared by the sync and async paths
([91]), and keep the offline seed at zero OpenAI calls.

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
- [ ] Migration with verified downgrade, if option 2
- [ ] `docs/database.md` updated if a table is added
