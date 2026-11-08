---
title: AI pre-review: rubric prompt and background job for new unreviewed questions
labels: [feature, ai-review, prompt, backend]
milestone: M3 AI-assisted review (advisory)
priority: P2
---

**Priority:** P2  **Milestone:** M3 — AI-assisted review (advisory)

## Summary

After an AI answer is saved as `UNREVIEWED`, run a second, cheaper call that
grades it against a fixed rubric and stores the result in `ai_reviews`.
Advisory only: it never changes `status`.

## Motivation

This is the first step of the automation roadmap and the one that produces
data for every later step. Running it in the existing background task (the
one that already translates) keeps latency for the student unchanged.

## Scope

- `services/ai_review_service.py` with `REVIEW_PROMPT_VERSION`.
- Rubric (score 0–2 each, plus a free-text rationale):
  physics correctness, mathematical correctness, completeness for the
  question asked, level fit (物理基礎/物理, no unrequested calculus),
  clarity for a struggling student, formatting rules ($, `\vec{}`, Markdown),
  scope (is it physics at all).
- Output: strict JSON (`verdict`, `confidence`, `reasons[]` from the #08
  codes, `rubric{}`, `rationale`, optional `suggested_answer`). Parse
  defensively; on parse failure store `verdict = null` with the raw text in
  `rationale` so failures are visible.
- The reviewer sees the question, the answer, the RAG context ids' approved
  answers (if any), and the concept list, in the question's language.
- Trigger: inside `translate_in_background` → rename to
  `post_generation_tasks`; also a CLI `review_pending --limit N` to backfill
  the existing queue.
- Cost control: one call per new AI answer; never on cache hits; skip when
  `settings.ai_review_enabled` is false (default false in tests).

## Acceptance criteria

- [ ] A new AI answer gets exactly one `ai_reviews` row within the request's
      background task.
- [ ] Malformed model output does not raise; the row records the failure.
- [ ] `status` is untouched in every case.

## Out of scope

- Showing the result (#14), measuring it (#15), acting on it (#18, #19).

## Technical notes

Use `deepseek_service.chat_completion`; consider a lower `max_tokens` for
this call. Keep the rubric text in `core/prompts.py` beside the answer
prompts so they evolve together.

## Dependencies

- Blocked by: #10, #12
- Blocks: #14, #15

## Definition of done

- [ ] Backend checks pass; tests with a mocked completion for valid,
      invalid, and off-topic outputs
- [ ] `docs/api.md` (CLI) and `docs/security.md` (cost note) updated
