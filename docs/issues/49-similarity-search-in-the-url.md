---
title: "[49] Put the vector search in the URL (?similar=...) and cache query embeddings"
labels: [feature, frontend, backend, student]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value

(Two drafts merged 2026-11-02: the git-bug `4444d02` body and the file
draft. The owner also decided the cost question the drafts had left open:
**store query embeddings** — see "Embedding cache" below.)

## Summary

Keyword search lives in the URL (`/?keyword=...`): shareable,
bookmarkable, restored by back/forward, and the destination of concept
chips (`/?concept=...`, [41]). The vector search has no URL form at all —
the query, the results, and even the fact that the similarity tab was
open vanish on reload. Give it one: `/?q=...`.

## Motivation

A student who found a good semantic match cannot send it to a classmate
or come back to it; the back button silently loses the search. Every
other way into the list is URL-addressable, so this is the odd one out —
and [43] (sticky ask bar) and [21] (help page examples) want linkable
searches too.

## Scope

- `?similar=<text>` drives the similarity search and implies the
  similarity tab; `keyword` keeps meaning the keyword tab, `concept` the
  chip list.
- On load with `similar` present, run the search **once** (the tab
  already uses an explicit button, not a debounce, so restore mirrors a
  click).
- Searching writes `similar` via the existing `useQueryState` pattern;
  clearing the box removes it. Never write it per keystroke.

## Embedding cache (owner's go-ahead, 2026-11-02)

Unlike `keyword` (a SQL `LIKE`), restoring `similar` costs an embedding call.
The owner approved storing query embeddings, which makes a restored or
shared search almost free:

- Table `query_embeddings`: `text_hash` (sha256 of the normalised query
  text + language), `embedding` (pgvector, same 1536 dims as questions),
  `model`, `created_at`, `last_used_at`, `hit_count`.
- Lookup by `(text_hash, model)`; miss → embed, insert, proceed. The
  `model` column matters: embeddings are only comparable within one
  model, so a model upgrade naturally invalidates the cache instead of
  silently corrupting search results.
- Normalise before hashing (trim, collapse inner whitespace, NFKC) so
  trivially different strings share one vector. Store the normalised
  text too, for inspection — the raw ask is already recorded elsewhere
  (`question_asks`), so this adds no new privacy surface.
- Eviction can wait: a vector is ~6 KB, so even 10k distinct queries are
  ~60 MB; `last_used_at` is there when a cleanup CLI becomes worth it.
- This also cuts the cost of *repeated manual* searches (students retry
  the same phrasing a lot), not just URL restores.

## Acceptance criteria

- [ ] Opening `/?similar=斜方投射` shows the similarity results without any click.
- [ ] Back/forward restores both tab and results; reload does not lose them.
- [ ] The search runs exactly once per restore (no double call in tests).
- [ ] A repeated query embeds nothing: the second search for the same
      normalised text makes zero OpenAI calls (backend test).
- [ ] Typing without submitting does not touch the URL.

## Out of scope

- Pagination of similarity results; evicting the cache (schema allows it
  later).

## Dependencies

- Blocked by: none. Related: [43] (the sticky bar should write the same
  URL), [21].

## Definition of done

- [ ] Backend (migration + cache) and frontend checks pass; vitest for
      restore-from-URL and submit-only; pytest for the cache hit path
- [ ] `docs/api.md` and `docs/development.md` note the parameter and the
      cache

## Log

- **2026-11-02** Implemented in commit 2513d20; all acceptance criteria
  pass (frontend vitest: write-on-submit, restore-once, clear-without-
  spending; backend pytest: second search embeds nothing, model change
  misses, RAG ask reuses a searched vector). One behaviour decided during
  implementation: a restored `?similar=` link **skips the exact-match
  redirect**, because restoring it on back-navigation would immediately
  push the student forward again - a restored link always shows the
  similarity results instead. Left open for the owner to verify in the
  UI; flip the row in status.md when satisfied.
