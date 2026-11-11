---
title: "[71] Stream /ai/ask answers (SSE) so students read while it generates"
labels: [backend, frontend, performance, feature]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67]

## Summary

Add a streaming variant of the ask endpoint: the answer arrives token by
token over Server-Sent Events, and the frontend renders it as it grows.
The student sees the first words in a couple of seconds instead of
watching a spinner for the whole generation. The only step in [67] that
changes what a student sees.

## Motivation

Even with the backend fully async, an uncached ask still takes as long
as DeepSeek takes — tens of seconds of a blank screen. Streaming does
not make generation faster; it makes the wait feel short, which is the
biggest perceived-latency win available to this system.

## Scope

Backend:

- `POST /ai/ask/stream`: same request schema, auth, rate limit and cache
  tiers as `/ai/ask`. A cache hit streams nothing special — it sends the
  full cached answer as one event. The existing JSON endpoint stays for
  compatibility (admin tools, tests, fallback).
- DeepSeek call with `stream=True` on the async client; forward chunks
  as SSE events; a final event carries what the JSON response carries
  today (`question_id`, `status`, `cached`, language).
- The off-topic sentinel appears at the start of the output: buffer the
  first chunks until the sentinel can be ruled in or out, then either
  stream the decline message (and save nothing) or start streaming the
  answer. A test pins this: no sentinel text ever reaches the client.
- Save the row and spend/record exactly as today once the stream
  completes; a client disconnect mid-stream must not leave a half-saved
  row (save happens after the full completion is collected, quota stays
  spent — the LLM call happened).
- Token usage still recorded (`stream_options.include_usage` or the
  final chunk's usage field, whichever the DeepSeek API provides).

Frontend:

- `lib/api/ai.ts`: a streaming ask using `fetch` + `ReadableStream`
  (EventSource cannot POST), with `useLatestRequest`-style staleness
  handling; fall back to the JSON endpoint on stream failure.
- The ask surfaces render the growing text through the existing
  `MarkdownContent` (KaTeX/CJK plugins unchanged); re-render throttled
  (e.g. per animation frame), partial markdown may look rough until the
  next chunk closes it — acceptable.
- Both languages: no new student-visible strings beyond perhaps a
  "generating…" state, which goes into the i18n tables (ja + en).

## Acceptance criteria

- [ ] First visible text within ~2 s of a cache-miss ask on a local
      stack (mocked-latency test asserts first-chunk-before-completion).
- [ ] Off-topic questions: the student sees only the decline message;
      nothing is saved; quota spent — identical to today.
- [ ] After the stream ends, the saved row equals what `/ai/ask` would
      have saved (text, metadata, tokens, ask history).
- [ ] Disconnect mid-stream leaves no UNREVIEWED half-row.
- [ ] Old endpoint behaviour unchanged.

## Out of scope

- Streaming any admin or review surface.
- Prompt changes (none; versions untouched).

## Technical notes

SSE over `StreamingResponse`; check CORS with credentials on the
streaming route (same middleware should cover it) and that Render's
proxy does not buffer SSE (`X-Accel-Buffering: no` / flush per event —
verify on the deployed stack before closing). `post_generation_tasks`
(translate, AI review) must run after the stream closes; with the
response already sent, schedule it the same way `BackgroundTasks` does
today or explicitly from the generator's end.

## Dependencies

- Blocked by: [70] (async DeepSeek client).
- Blocks: none.

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Frontend: `npm run lint`, `tsc --noEmit`, `npm test`, `npm run build` pass
- [ ] `docs/api.md` documents the streaming endpoint and its events
- [ ] Manual check on the local Docker stack in both languages
