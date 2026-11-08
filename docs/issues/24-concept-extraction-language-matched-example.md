---
title: "[24] Concept extraction prompt: language-matched worked example (v3)"
labels: [prompt, backend, data-quality]
milestone: M2 Review data foundation
priority: P3
---

**Priority:** P3  **Milestone:** M2 — Review data foundation

## Summary

The concept-extraction prompt's worked example is Japanese-only even when
the question and answer being processed are English. Add an English example
and pick it by the row's language; bump `CONCEPT_EXTRACTION_PROMPT_VERSION`
to `v3`.

## Motivation

Audit of all prompts (2026-10-29):

| Prompt | Student-facing? | Language handling | Gap |
| --- | --- | --- | --- |
| `SYSTEM_PROMPTS` (answer) | yes | separate ja / en texts | none |
| `RAG_SYSTEM_PROMPTS` + `RAG_CONTEXT_LABELS` | yes | separate ja / en | none |
| `OFF_TOPIC_FALLBACK` | yes | ja / en | none |
| `TRANSLATE_*` | no | one English instruction, `source`/`target` parameters, bilingual glossary | none - direction-agnostic by design |
| Concept extraction (`concept_service`) | no | one English instruction, `language_name` parameter, output format `<ja> \| <en>` | **worked example is Japanese-only** |

For machine-processing prompts the *instruction* language is a non-issue -
one English instruction keeps the output format identical for both
languages, which the parser relies on. But few-shot examples steer the
model strongly, and an English Q&A paired with a Japanese-only example
invites Japanese-flavoured or mis-split output.

## Scope

- Add `_EXAMPLE_EN` (an English physics Q&A with the same `<ja> | <en>`
  output lines) beside the existing Japanese example; choose by `language`.
- `CONCEPT_EXTRACTION_PROMPT_VERSION = "v3"`; existing `question_concepts`
  rows keep their recorded version.
- Keep the instruction text in English; do not add a Japanese instruction
  variant (reasoning above - say so in a code comment).
- Rule for future prompts, to add to `AGENTS.md`: anything a student reads
  must exist in both languages and be selected by the request language;
  machine-processing prompts may use one instruction language but must
  carry language-matched examples and bilingual vocabulary (glossary).

## Acceptance criteria

- [ ] Extraction for an English row sends an English example; for a
      Japanese row the Japanese one (prompt snapshot test).
- [ ] Output parsing unchanged; existing concept tests pass.

## Out of scope

- Re-extracting concepts for existing rows (admin bulk action already
  exists if wanted).

## Dependencies

- Blocked by: none
- Blocks: none (the AI reviewer prompt in [13] must follow the same rule
  from the start: per-language rubric text)

## Definition of done

- [ ] Backend checks pass
- [ ] `AGENTS.md` gains the bilingual-prompt rule
