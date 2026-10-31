---
title: Schema for AI reviews: ai_reviews table and reviewer_kind
labels: [feature, ai-review, review, backend]
milestone: M2 Review data foundation
priority: P2
---

**Priority:** P2  **Milestone:** M2 — Review data foundation

## Summary

Add a place to store an AI reviewer's verdict next to, but separate from,
human reviews, and mark which kind of reviewer produced each history row.

## Motivation

Mixing AI verdicts into `question_reviews` would make the human history
ambiguous; keeping them apart lets #15 measure agreement cleanly and lets
#18/#19 later write *actual* status changes as `reviewer_kind = 'ai'` rows
when a policy is allowed to act.

## Scope

- Migration: `ai_reviews` (`id`, `question_id` FK CASCADE, `language`,
  `verdict` APPROVE/EDIT/REJECT, `confidence` 0–1, `reasons` text[] using
  the #08 codes, `rationale` text, `suggested_answer` text nullable,
  `rubric` jsonb (per-criterion scores), `model`, `prompt_version`,
  `prompt_tokens`, `completion_tokens`, `created_at`). Index on
  (`question_id`, `created_at`).
- `question_reviews.reviewer_kind` (`human` default, `ai`, `policy`),
  nullable `policy_name`.
- Repository + Pydantic schemas; no behaviour yet.

## Acceptance criteria

- [ ] `test_models_match_migrations` passes; downgrade verified.
- [ ] Existing review rows read back as `reviewer_kind = 'human'`.

## Out of scope

- Running any model (#13).

## Technical notes

Follow the `rate_limit_hits` migration style. `rubric` as `jsonb` keeps the
criteria list changeable without migrations.

## Dependencies

- Blocked by: #08 (reason codes)
- Blocks: #13, #14, #15

## Definition of done

- [ ] Backend checks pass
- [ ] `docs/database.md` updated with the table and ERD line
