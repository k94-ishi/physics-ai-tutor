---
title: "[77] Question page: three requests in two waves become one wave"
labels: [frontend, performance]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67]

## Summary

Opening a question makes three requests (`/{id}`, `/prerequisites`,
`/related`) in two waves: the detail first, then the other two. The
second wave does not actually depend on the first, so the page can start
all three together and save a full round trip before anything appears
below the answer.

## Motivation

Raised by a coworker as "three separate requests per question page"
(2026-11-11). Checked: `QuestionDetail.tsx` already runs prerequisites
and related **in parallel** (`Promise.allSettled`, line 92), so the count
is not the problem — the *serialisation* is. Both of those calls need
only `id` and `language`, both of which are known before the detail
response arrives, yet they wait for it (line 66).

On top of that the page is a client component gated on
`useLanguage().resolved` ([53]), so the browser must load and hydrate JS
before the first request even starts. The related/prerequisite queries
are the expensive ones (concept lookups and vector work), so the extra
wave lands exactly where it hurts.

## Scope

- Start all three fetches in one wave in `QuestionDetail`, keeping each
  block's independent failure handling (`allSettled`) and the
  `useLatestRequest` staleness guard from [63]. The detail still renders
  as soon as it arrives; the lower blocks fill in when they do.
- Keep the 404 path correct: a missing question must still show "not
  found" and must not leave the related blocks spinning.
- Keep the [53] rule: never show the previous language's results after a
  switch.
- Check the same two-wave pattern on the other pages that load a
  question plus extras (home preview modal [56], admin queue) and fix any
  found; list what was checked in the Log.
- Measure with the browser's network panel on the local stack: time to
  the answer, and time to the "read these first" block, before and after.

## Acceptance criteria

- [ ] All three requests leave together; the related block appears about
      one round trip sooner.
- [ ] 404, load-error, and language-switch behaviour unchanged (existing
      tests plus one new test that the three fetches are issued
      concurrently).
- [ ] No duplicate fetch on mount or on language resolution.

## Out of scope

- Combining the three endpoints into one API response. It would cut the
  round trips to one, but it changes the API surface and couples three
  independent blocks into one failure domain — file a separate issue if
  the measurement shows one wave is still too slow.
- Moving the page to a server component (same reason: bigger change,
  interacts with the language-in-URL rule [50]).

## Technical notes

`fetchQuestion`'s result is not an input to the other two calls — verify
that stays true if the prerequisite logic ever starts from the detail's
concepts. Server-side rendering uses `INTERNAL_API_URL`; this issue does
not change which side fetches.

## Dependencies

- Blocked by: [68] (to measure). Independent of the backend conversions.
- Blocks: nothing.

## Definition of done

- [ ] Frontend: `npm run lint`, `tsc --noEmit`, `npm test`,
      `npm run build` pass
- [ ] Before/after timings in this issue's Log
- [ ] Manual check on the local Docker stack in both languages
