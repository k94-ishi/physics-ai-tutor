---
title: "[55] Concepts as language-neutral senses with many terms per language (位相 = phase / topology, speed = 速さ / 速度)"
labels: [feature, backend, frontend, i18n, data-quality, design]
milestone: M1 Student value
priority: P1
---

**Priority:** P1  **Milestone:** M1 — Student value

## Summary

A concept today is one row with exactly one Japanese and one English name,
each globally unique. Real terminology is many-to-many: 位相 is "phase" in
waves and "topology" in maths; "speed" means 速さ, but students also say it
for 速度; "phase" is both 位相 (waves) and 相 (気相, states of matter).
Owner's requirement (2026-11-09): a student must find a QA by searching in
**either language**, even when the two languages do not pair 1:1; a general
structure, not a glossary of special cases, even if it costs more to build.

Proposal: split the concept into a **sense** (the meaning, language-neutral)
and its **terms** (the words for it, any number per language, shared words
allowed across senses).

## The defect this also fixes

`concept_service._find_existing` matches a newly extracted pair by the
Japanese name, else by the English name. So today:

- `相 | phase` is attached to the existing `位相 | phase` concept (English
  match) - states-of-matter QAs silently join the wave-phase concept.
- `位相 | topology` is attached to `位相 | phase` (Japanese match).

The unique constraints on `name_ja`/`name_en` force this: two senses cannot
share a word, so the code merges them.

## Proposed structure

```
concepts (sense)            concept_terms
- id                        - id
- gloss_ja, gloss_en        - concept_id  FK -> concepts, CASCADE
  (short disambiguation,    - language    ja | en
   e.g. 波の位相 / of a wave)- term        e.g. phase
- embedding (of the sense)  - normalized  NFKC, lower-case, trimmed
- provenance columns        - is_preferred  one per (concept, language)
                            - source      EXTRACTED | MACHINE | TEACHER
question_concepts unchanged - UNIQUE (concept_id, language, normalized)
(links a QA to a sense)     - index (language, normalized) - NOT unique
```

- A QA links to a **sense**, so the link is language-independent: a
  Japanese-only QA about 位相 (waves) is found from the English term "phase".
- The same word may belong to several senses: that is the polysemy, stored
  honestly instead of being forbidden.
- `is_preferred` picks the label shown on chips; other terms are aliases
  (速度 has preferred "velocity" and alias "speed").
- `source` keeps machine-made terms reviewable (AGENTS.md: keep educational
  content reviewable).

## How each case behaves

| Case | Stored | Student searches | Result |
| --- | --- | --- | --- |
| 位相 (waves) / 位相 (topology) | two senses, each with ja term 位相 | 位相 | both senses offered, labelled by gloss; topology has no QAs in this app, so in practice one |
| "phase" = 位相 / 相 | two senses, each with en term "phase" | phase | "phase - of a wave (12)" / "phase - state of matter (4)" |
| "speed" = 速さ / 速度 | 速さ: en "speed" (preferred); 速度: en "velocity" (preferred) + alias "speed" | speed | both senses; 速さ first (preferred match ranks above alias) |
| Japanese-only QA | sense with ja term only; en term filled later | English term | found through the sense; text shown after [53]'s translation |

## Matching at extraction (no prompt change)

Extraction already returns `<ja> | <en>` pairs. Replace name-equality
matching with:

1. Candidates = senses having a term equal (normalized) to either name.
2. One candidate whose terms agree on both sides -> attach.
3. Several candidates, or only one side matches -> pick by cosine similarity
   between the embedding of the pair (`位相 | phase`) and each sense
   embedding; attach above a threshold (tuned on the local corpus), else
   create a new sense. The pair is embedded today already (one embedding
   call per new concept), so no extra API cost.
4. On attach, add any new word as a term (`source=EXTRACTED`), never
   overwrite the preferred one.

Missing-language terms from [53]'s background translation become
`source=MACHINE` terms; translation now passes a QA that uses the concept
as context so the translator sees "波の位相とは？", not a bare word.

## Search and display

- `GET /api/v1/concepts?q=&lang=` ([41]'s concept filter) searches terms in
  **both** languages, returns senses with their label in `lang`, gloss, and
  question count. Exact preferred-term matches rank first.
- `?concept=<id>` addresses a sense unambiguously. A typed or legacy
  `?concept=<name>` resolves through terms; one sense -> its list, several
  -> a small "which one?" choice.
- Chips show the preferred term in `lang`; when two senses on one page share
  a label, the gloss is appended.
- Keyword search (optional, phase 4): expand a keyword with the senses whose
  terms match it.

## Admin review

`/admin/manage/concepts`: list senses with terms per language and source;
edit gloss, add/remove an alias, change the preferred term, **merge** two
senses (re-link QAs) and **split** one (move QA links). Machine terms are
flagged until a teacher touches them.

## Phases (each shippable, each with tests)

1. **Schema**: `concept_terms` + gloss columns; migration copies
   `name_ja`/`name_en` into preferred terms; old columns kept (additive,
   per docs/database.md). Read paths (chips, prerequisites `_defines`,
   `?concept=`) use terms. No visible change.
2. **Matching**: new extraction matching; drop name uniqueness; [53]'s
   translation writes terms with context. Re-check the local corpus for
   senses that were merged by the old rule (a one-off report CLI).
3. **Search**: concept endpoint and filter over terms ([41]), sense ids in
   URLs, disambiguation UI.
4. **Admin editor**: merge/split/alias/preferred/gloss.
5. **Cleanup**: drop `name_ja`/`name_en` once nothing reads them.

## Acceptance criteria

- [ ] `相 | phase` and `位相 | phase` end up as two senses sharing the en term.
- [ ] Searching "phase" offers both senses; searching 位相 finds the wave QAs.
- [ ] Searching "speed" returns QAs of both 速さ and 速度, 速さ first.
- [ ] A Japanese-only QA is found from an English term.
- [ ] Machine-made terms are visible as such in the admin editor.

## Out of scope

- Hand-authored ontology / hierarchy between senses (broader/narrower).
- Prompt changes (owner, 2026-11-09: not now).

## Dependencies

- Supersedes the name-collision handling of [53].
- Blocks: [41]'s concept filter (build it on terms, not names).
- Related: [38] (definers matched by term), [54] (production migration).
