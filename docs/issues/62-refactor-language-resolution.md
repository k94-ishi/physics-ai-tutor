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

### 2026-11-11 - done

- `services/response_language.py`: `ResponseLanguage(language, strict)`,
  built once per request (`for_caller(lang, admin)`), and
  `TranslationNeeds(question_ids, concept_question_ids)`.
- Removed everywhere in services and routers: `strict_language`,
  `only_with_language`, `translate_if_missing`, the `missing_language_ids`
  out-lists and `split_by_language`. Services take `language=` (a plain
  Language = admin fallback) and return their needs:
  `get_related_questions` -> `RelatedQuestions(items, needs)`,
  `get_prerequisites` -> `Prerequisites(response, needs)`,
  `fetch_question` -> `(question, needs)`; `prepare_for_response` returns
  the needs of what it presented.
- The router's two queue helpers became one `_queue_translations(needs)`.
  Concept-name checks still run only where they ran before (detail,
  related, prerequisites - the current QA first); list and exact-match
  queue nothing, as before.
- Kept: filter before slicing (a student still gets `limit` readable rows).
- Scope added from [60]: `QuestionFilters` (keyword, status, statuses,
  search fields, language, AI verdict, ids, concept) replaces the 16
  parameters passed twice; `fetch_questions` body 52 -> 25 lines; the
  repository's `get_questions`/`count_questions` take the same object.
- Tests: `test_language_strict.py` and `test_language.py` pass unchanged;
  16 direct-call tests updated to the new signatures by an AST rewriter
  (assertions untouched); new `test_response_language.py` (4).
  OpenAPI schema identical. pytest 529 (~31 s), ruff, mypy.
