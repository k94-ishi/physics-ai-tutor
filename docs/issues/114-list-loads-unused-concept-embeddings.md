---
title: "[114] The question list loads every concept's embedding vector it never uses"
labels: [backend, performance]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67] (found in [99])

## Summary

`GET /questions` loads each listed question's concepts as full `Concept`
rows, including the 1,536-number `embedding` vector, to show only the
concept names. Parsing those vectors is CPU work that grows with the
page size; skipping the column should make the list much cheaper.

## Motivation

Found while re-measuring the connection budget in [99] (2026-11-17), on a
busy machine (load 3-12 on 8 cores, other sessions benchmarking too):

- Sequential, one worker: `/health` 1 ms, `/db-health` 23 ms,
  `/questions?size=5` 117 ms, `/questions?size=50` 143-1,380 ms (the
  spread is machine load).
- The request runs a constant 6-8 SQL statements whatever its size, so it
  is not an N+1. The timestamps put ~0.5 s between the concept query
  (`question_concepts.question_id, concepts.*`, which selects
  `concepts.embedding`) and the next statement.
- Being CPU work, it does not overlap: at concurrency 32 throughput stayed
  ~5 requests/s and the pool filled to its ceiling while requests queued.

[75] measured 99 ms p50 at concurrency 32 on 2026-11-12; the same query
shape existed then, so this is most likely load-sensitivity rather than
a code regression - to be confirmed on a quiet machine first.

## Scope

- Measure `/questions?size=50` sequentially on a quiet machine to get a
  clean baseline.
- Load only the columns the list needs: e.g. `defer(Concept.embedding)`
  (or `load_only`) in `question_concept_repository._concepts_for_questions_select`,
  checking every caller of that statement still gets what it reads.
- Re-measure with the [68] probe; record both numbers here.

## Acceptance criteria

- [ ] The list query no longer selects `concepts.embedding`.
- [ ] Before/after numbers recorded; response bodies unchanged (tests).

## Dependencies

- Blocked by: none
- Blocks: none; fits beside [74]/[77]
