---
title: "[80] Tuning constants: collect and document them, but keep them out of the environment"
labels: [backend, frontend, config, docs]
milestone: M1 Student value
priority: P3
---

**Priority:** P3  **Milestone:** M1 — Student value  **Track:** [81]

## Summary

The remaining hard-coded numbers decide *what a student sees* — how many
related questions, how similar is similar enough, how concepts are
matched. Collect them in one documented place per side, explain what
moving each one does, and deliberately **do not** turn them into
environment variables.

## Motivation

Owner's observation (2026-11-11) was that many parameters are
hard-coded. [79] moves the operational ones. This issue is the answer
for the rest, and the answer is mostly "they stay, but they should stop
being scattered and unexplained".

The reason to keep them in code: each one changes retrieval or
presentation quality, so a change should go through review, the golden
eval set ([17]) and the difficulty-rating evaluation ([52]) — not
through an env var someone can set on Render at 2am with no record of
why. An operator changing `RAG_MIN_SCORE` is making an editorial
decision about the product, not an operational one.

They also cannot usefully be env vars on the frontend: `NEXT_PUBLIC_*`
is inlined at build time, so a "configurable" value there still needs a
rebuild and deploy, with none of the review.

## Scope

Backend — gather into one module (or clearly flag in place) with a
sentence each on what raising and lowering it does:

| Constant | Where | Decides |
| --- | --- | --- |
| `RAG_TOP_K = 5`, `RAG_MIN_SCORE = 0.5` | `rag_service` | How much grounding an answer gets |
| `QUESTION_SIMILARITY_WEIGHT = 0.7`, `CONCEPT_SIMILARITY_WEIGHT = 0.3`, `CANDIDATE_POOL_SIZE = 50` | `recommendation_service` | The related-questions ordering |
| `concept_sense_match_threshold = 0.75` | `config.py` (already a setting) | Whether an extracted pair joins an existing sense ([55]) — consider demoting it to a code constant for the same reason |
| `MAX_LEVEL = 4` | `concept_service` | The difficulty scale ([40]) |
| `MAX_PARSE_ATTEMPTS = 3`, `MAX_ESCAPE_REPAIRS = 500` | AI review | How hard we try to salvage malformed reviewer JSON |
| `MAX_ID_FILTER = 100` | `api/v1/questions.py` | Admin id-search cap; mirrored by `MAX_ID_SEARCH` in the frontend |

Frontend — same treatment, in one place:
`RELATED_FETCH_LIMIT = 20`, `RELATED_VISIBLE = 10`
(`QuestionDetail.tsx`), `RUN_POLL_INTERVAL_MS = 2500`
(`useAiReviewRun`), default `limit` values in `lib/api/*`.

Also:

- The two id caps (`MAX_ID_FILTER` backend, `MAX_ID_SEARCH` frontend)
  are the same rule written twice. Keep them equal and note that the
  backend one is the real limit; a test on the frontend constant can
  assert the documented value.
- Write the decision itself down in `docs/development.md`: which
  parameters are environment variables ([79]), which are code constants
  (here), and why the line falls where it does. That note is the lasting
  output of this issue.

## Acceptance criteria

- [ ] Every constant above is findable from one place per side and has a
      one-line explanation of its effect.
- [ ] `docs/development.md` states the env-var-versus-constant rule.
- [ ] Backend and frontend id caps are documented as one rule and are
      equal.
- [ ] No behaviour change: every value keeps its current number.

## Out of scope

- Actually retuning any value. A change to `RAG_MIN_SCORE` or the
  similarity weights needs evidence from the eval sets ([17], [52]) and
  belongs in its own issue.
- Making these settable per request or per user.

## Technical notes

Collecting constants must not create an import cycle: a shared
`core/tuning.py` that imports nothing from services is safer than a
module services already import from. If a constant is genuinely local to
one service and never read elsewhere, leaving it there with a comment is
fine — the deliverable is that someone can find and understand all of
them, not that they live in one file.

## Dependencies

- Blocked by: none. Independent of the async work.
- Related: [79] (the other side of the line), [17] and [52] (the
  evidence any retuning would need).

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Frontend: `npm run lint`, `tsc --noEmit`, `npm test`,
      `npm run build` pass
- [ ] `docs/development.md` carries the rule and the inventory
