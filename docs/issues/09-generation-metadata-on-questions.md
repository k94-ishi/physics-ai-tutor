---
title: Record generation metadata on AI-generated questions
labels: [feature, review, data-quality, backend, prompt]
milestone: M2 Review data foundation
priority: P1
---

**Priority:** P1  **Milestone:** M2 — Review data foundation

## Summary

Store which model, prompt version, and mode produced each AI answer, so
review outcomes can be compared across prompt changes.

## Motivation

`concept_service` already has `CONCEPT_EXTRACTION_PROMPT_VERSION = "v2"`,
but answer generation records nothing: a question row cannot tell you
whether its answer came from the current system prompt or last month's, nor
from `deepseek-chat` or a later model. Without this, approval rates before
and after a prompt change are not comparable, and #17/#20 are impossible.

## Scope

- Migration: nullable columns on `questions`: `generation_model`,
  `prompt_version`, `generation_mode` (`DIRECT` / `RAG`),
  `prompt_tokens`, `completion_tokens`. Null for manual and imported rows.
- `prompts.ANSWER_PROMPT_VERSION` constant, bumped on every prompt edit
  (enforce with a short note in `prompts.py` and a test that the constant
  changes when the prompt text hash changes).
- `deepseek_service.chat_completion` returns usage alongside content (or a
  small dataclass); `save_ai_question` stores it.
- Expose in admin `QuestionResponse` only.

## Acceptance criteria

- [ ] A new AI answer row has model, version, mode, and token counts.
- [ ] Manual rows keep nulls; public responses do not include the fields.

## Out of scope

- Storing the full prompt text (version + git history is enough).

## Technical notes

`retrieved_question_ids` already captures RAG context; keep it.

## Dependencies

- Blocked by: none
- Blocks: #11, #15, #17, #20

## Definition of done

- [ ] Backend checks pass; migration downgrade verified
- [ ] `docs/database.md` updated
