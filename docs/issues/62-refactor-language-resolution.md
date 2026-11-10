---
title: "[62] One language-resolution step for responses instead of flags and out-parameters"
labels: [refactor, backend, i18n]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [57]

## Summary

[53] made the strict-language rule work by threading `strict_language`,
`only_with_language` and a `missing_language_ids` out-list through four
call chains. Replace that with one explicit step.

## Proposal

- A `ResponseLanguage` value (`lang`, `strict: bool`) built once from the
  request (admin -> fallback, student -> strict).
- `present(questions, ResponseLanguage) -> Presented(items, missing_ids,
  missing_concept_ids)`: resolves text, filters, attaches tags and
  references, and reports what needs translation.
- Routers pass `Presented.missing_*` to the background translator; no
  service takes an out-parameter.
- Ranking services return candidates; filtering happens before slicing
  inside `present` (keep the [53] "full count from readable rows" rule).

## Acceptance criteria

- [ ] No `missing_language_ids` parameters remain.
- [ ] `test_language_strict.py` and `test_language.py` pass unchanged.

## Dependencies

- Blocked by: [60] (smaller modules to change)

## Log

### 2026-11-11 - scope addition from [60]

Also introduce a typed question filter object (keyword, status, concept, ids, language...) shared by the list router, `question_read_service.fetch_questions` and the repository, replacing the 16 parameters passed twice.
