---
title: "[50] Put the content language in the URL so shared links mean the same thing for everyone"
labels: [feature, frontend, student, i18n]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value

## Summary

The UI/content language lives only in `localStorage`
(`LanguageContext.tsx`, key `language`, default `ja`). Every other piece
of list state is now in the URL — `keyword`, `concept` ([41]),
`similar` ([49]) — so language is the last hidden input, and it is the
one that changes what the other three *return*. Owner's question,
2026-11-02.

## Motivation

This is not only cosmetic, because **the vector search is
language-scoped**: `search_similar_questions` filters embeddings by
language, and the client passes the active language. So a shared link
can silently behave differently for the recipient:

| link | sender (ja) | recipient whose stored language is en |
| --- | --- | --- |
| `/?similar=斜方投射` | Japanese results | searches the *English* embeddings for a Japanese string — few or no results |
| `/?concept=微分方程式` | the concept's questions | same concept name, but the list is filtered to rows having English text |
| `/?keyword=...` | matches any language column | same results, English UI |

The failure is quiet: the recipient sees an empty or odd list and has no
hint that a language setting caused it. The same applies to any example
links the help page ([21]) will carry.

## Scope

- `?lang=ja|en` read by `LanguageProvider` on mount, **URL wins over
  localStorage**; absent `lang` keeps today's behaviour (stored value,
  else `ja`), so ordinary browsing URLs stay clean.
- The header language switcher updates `?lang=` when the parameter is
  already present (a shared link keeps meaning what it says while you
  browse it), and always updates localStorage as now.
- Decide and document one rule: does switching language *keep* a
  `similar=` query (re-running it against the other language's
  embeddings) or clear it? Recommendation: keep it and re-run — the
  student asked for that text, and an empty result is honest feedback
  that the other language has no matching content.
- `/questions/{id}` already falls back to the original language, so it
  needs nothing beyond honouring `?lang=`.

## Acceptance criteria

- [ ] `/?lang=en&similar=projectile+motion` renders the English UI and
      English results for a visitor whose stored language is `ja`, and
      does not overwrite their stored preference silently (or does, but
      documented — pick one and test it).
- [ ] A URL with no `lang` behaves exactly as today.
- [ ] Switching language on a link that carries `lang` updates the URL.

## Out of scope

- Per-language routes (`/ja/...`, `/en/...`); server-side language
  negotiation from `Accept-Language`; translating URLs themselves.

## Dependencies

- Related: [49] (the parameter whose results depend on language), [41],
  [21].

## Definition of done

- [ ] Frontend checks pass; vitest for URL-wins-over-storage and for the
      no-parameter default
- [ ] `docs/development.md` lists `lang` with the other list parameters
