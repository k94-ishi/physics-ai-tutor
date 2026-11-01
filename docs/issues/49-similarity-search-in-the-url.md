---
title: "[49] Put the vector search in the URL, like keyword and concept"
labels: [feature, frontend, student]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value

## Summary

Discovery state lives in the URL for two of the three ways in:
`/?keyword=XXX` (lexical) and `/?concept=YYY` ([41]). The vector search
has none: `QuestionSearchAndAsk` keeps its query in `useState`
(`src/components/QuestionSearchAndAsk.tsx:86`), so a similarity search
cannot be shared, bookmarked, or restored with the back button. Owner's
observation, 2026-11-01.

## Motivation

- **Back-button loss is the sharpest cost.** A student searches, opens a
  result, presses back - and the search is gone. With [42]'s preview
  modal this hurts less, but following a link out still loses it.
- **Sharing**: a teacher cannot send "search for this and look at what
  comes back".
- **Consistency**: once two of three entry points are URL-addressable,
  the third being invisible is a surprise, and the mode tab is not
  restorable either.

## Scope

- Query parameter `similar=` (recommended over `q=`: it sits beside
  `keyword=` and `concept=` and says which search it is).
- Presence of `similar=` selects the similarity tab on load, so the link
  opens the right mode; add the mode to the URL only if it turns out to
  be needed beyond that.
- Write the parameter **on submit, not per keystroke** - unlike
  `keyword=`, which is debounced and free. See the cost note below.
- Restore on load: run the search once for the parameter's value.
- Clearing the box clears the parameter.

## Cost note (why this is not simply keyword's twin)

A lexical search is a SQL `LIKE`; a vector search costs an embedding API
call per execution. Making it URL-driven means any load of that URL
spends one - including repeat visits and any crawler that ignores
`robots.txt` (the site is `Disallow: /` apart from `/privacy`, so this
is small but not zero). Hence: submit-only writes, one search per
distinct parameter value, and no debounced URL churn. If this ever looks
expensive, cache the embedding for the exact query string.

## Acceptance criteria

- [ ] Submitting a similarity search puts `?similar=...` in the URL.
- [ ] Opening that URL directly shows the similarity tab with the same
      results, after exactly one search request.
- [ ] Back after opening a result restores the search and its results.
- [ ] Typing without submitting does not touch the URL.

## Out of scope

- Caching embeddings; changing the keyword or concept parameters.

## Definition of done

- [ ] Frontend checks pass; vitest for restore-from-URL and submit-only
- [ ] `docs/api.md` unchanged (no API change); note the parameter in the
      component's docstring
