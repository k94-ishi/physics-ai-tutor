---
title: Ground the AI reviewer in similar past human reviews
labels: [feature, ai-review, prompt, backend]
milestone: M3 AI-assisted review (advisory)
priority: P3
---

**Priority:** P3  **Milestone:** M3 — AI-assisted review (advisory)

## Summary

Before grading, retrieve the k most similar previously human-reviewed
questions (by the existing embeddings) and include their verdict, reason,
and before/after answers as examples in the reviewer prompt.

## Motivation

This is how the human review history improves the AI reviewer without any
fine-tuning: teachers' past decisions on similar questions become in-context
examples. It reuses the pgvector search and the RAG prompt-building code, and
it is measurable with #15 (compare agreement with and without examples).

## Scope

- `ai_review_service`: retrieve top-3 reviewed questions above a similarity
  threshold, in the same language, prefer rows with `EDIT_APPROVE` or
  `REJECT` and a reason; format as "Example review" blocks.
- Token budget: cap each example's answer length; skip examples when the
  total would exceed a configurable limit.
- Record the example ids in `ai_reviews.rubric` (or a new `example_ids`
  column) so the influence can be audited.
- A/B: `settings.ai_review_examples_enabled`; #15 groups by it.

## Acceptance criteria

- [ ] With examples enabled, the prompt contains at most 3 example blocks
      drawn only from human-reviewed questions.
- [ ] Agreement on a held-out set is reported with and without examples.

## Out of scope

- Fine-tuning any model; building a separate vector index.

## Technical notes

Similar questions whose human verdict was `REJECT` for `OFF_TOPIC` are
especially valuable as negative examples.

## Dependencies

- Blocked by: #13, #15 (to measure the effect), #11 (held-out set)
- Blocks: none

## Definition of done

- [ ] Backend checks pass; prompt snapshot test
- [ ] `docs/security.md` notes that review history text is sent to the LLM
