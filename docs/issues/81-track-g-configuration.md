---
title: "[81] Track G: configuration - what belongs in the environment and what belongs in code"
labels: [epic, roadmap, config]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value

Owner's observation (2026-11-11), while reviewing [69]'s explicit pool
settings: there are a lot of parameters in the codebase and they are
hard-coded. This track answers that, and the answer is not "move
everything into environment variables".

## The line this track draws

A parameter belongs in the **environment** when the reason to change it
is operational: load, cost, an incident, a database plan limit. Changing
it should not need a code review, because the person changing it is
reacting to something.

A parameter belongs in **code** when the reason to change it is
editorial: it decides what a student sees. Changing it should need a
review and evidence from the eval sets ([17], [52]), because the person
changing it is making a product decision. `RAG_MIN_SCORE` is the clear
case — an operator who lowers it at 2am has changed what counts as a
grounded answer, with no record of why.

Frontend constants fall on the code side almost by construction:
`NEXT_PUBLIC_*` is inlined at build time, so a "configurable" value
there still needs a rebuild and a deploy, with none of the review.

## Steps

1. [78] Config hygiene: fix the wrong defaults (including the
   `loaclhost` typo), validate values at startup instead of failing
   later, and stop the drift between `Settings`, `.env.template` and the
   docs table.
2. [79] Operator-tunable settings: rate limits, pool sizes, run timeout,
   cleanup probability and the LLM timeout become settings, each keeping
   today's value as its default.
3. [80] Tuning constants: collect and document the rest, keep them in
   code, and write the rule itself into `docs/development.md`.

Order matters only in that [78] makes [79] safer — validation lands
before new variables rely on it. All three are independent of Track F
([67]) and can be picked up between its steps.

## Rules

- No behaviour change: every parameter keeps its current value as the
  default. Retuning anything is a separate issue with evidence.
- A new setting is read where it is used, never captured into a module
  constant at import, or overriding it silently does nothing.
- Security-relevant numbers (rate limits) get validation, and
  `docs/security.md` must say they are defaults rather than fixed.

## Dependencies

- Related: [70] (adds the LLM request timeout), [72]
  (`AI_REVIEW_CONCURRENCY`), [74] (pool tuning against the Supabase
  pooler), [75] (worker count, which multiplies the pool).
