---
title: "[85] Asynchronize the admin review workflow: review, bulk review, history, translate, re-extract"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], slice 4 of [73]

## Summary

Convert the five admin routes a teacher uses every day in the review
queue - approve / edit-approve / reject, bulk review, review history,
fill missing translations, re-extract concepts - and the services
behind them. No change in what is recorded or shown.

## Motivation

These are the routes [73]'s summary singled out: review endpoints with
translation and extraction side effects. An approve can call DeepSeek
for concept extraction and a translation, so today one click holds a
server thread for seconds; a bulk approve holds it for many. On the
async stack the wait costs nothing, and the LLM calls move out of the
transaction ([82]), which this path still violates
(`reextract_concepts_for_questions` is on the [82] allowlist).

## Scope

- Routes in `api/v1/admin_questions.py`: `GET /questions/{id}/reviews`,
  `POST /questions/{id}/review`, `POST /questions/bulk-review`, `POST
  /questions/translate`, `POST /questions/concepts/extract`.
- `question_review_service` (six functions) and
  `question_review_repository` (three): single caller, convert outright.
- `question_write_service.reextract_concepts_for_questions`,
  `extract_concepts_best_effort`, `attach_concepts_best_effort`, and the
  extraction path of `concept_service` (prompt call through
  `deepseek_service.async_chat_completion`, sense matching, linking).
  Shape it as prepare (LLM call, no session) then apply (short
  transaction that links concepts), so the allowlist entry for
  `reextract_concepts_for_questions` is removed here.
- `question_translation_service`: edit-approve regenerates the machine
  counterpart (`refresh_machine_translations`, `embed_language`), and
  `/translate` already has `async_translate_missing_languages`. Add
  `async_` twins for the functions edit-approve needs; the sync ones
  stay for create/import until [86].
- Write functions of `question_repository` (`update_status`, text
  setters), `question_concept_repository` (`link`, `link_many`,
  `delete_by_question_id`) and `embedding_repository` (delete and
  insert by question and language): twins, since [86] still needs the
  sync ones.
- The approve path keeps doing what it does today (extraction and
  translation inline, not deferred) - this is a conversion, not a
  behaviour change.

## Acceptance criteria

- [ ] The five routes are `async def` on `get_async_db`.
- [ ] Review rows identical: action, reason, language, before/after
      snapshots, `reviewer_kind`; `EDIT_APPROVE` still regenerates a
      `MACHINE` counterpart; bulk `REJECT` still requires one reason;
      `OTHER` still requires a comment.
- [ ] `test_architecture.py`'s [82] allowlist no longer contains
      `reextract_concepts_for_questions`, and
      `test_llm_connection_discipline.py` gains a probe: no transaction
      is open when concept extraction is called during an approve.
- [ ] `test_review_workflow.py`, `test_review_reasons.py`,
      `test_concept_service.py` and the review half of
      `test_question_service.py` green.

## Out of scope

- Create, update, delete, import ([86]).
- AI review runs and the admin stats routes ([87]).
- Deferring extraction or translation to a background task - a
  behaviour change; file it separately if wanted.

## Technical notes

Reference on `wip/73-async-remaining`:
`git diff 260d7c2 9c42cfd -- backend/physics_ai_tutor/services/{question_review,concept}_service.py backend/physics_ai_tutor/repositories/question_review_repository.py`.
The WIP collapsed `concept_service`'s twins and dropped the sync
`embed_language`; this slice keeps those sync functions alive for [86]
and the seed.

Test churn estimate: about 40 tests (`test_review_workflow` 7,
`test_review_reasons` 8, `test_concept_service` 11, ~15 review tests in
`test_question_service`); the API tests in `test_questions.py`,
`test_language.py` and `test_ai_review_queue.py` exercise the routes
through `client` and should need little change.

Capture scalars (`question.id`, status) before the apply transaction:
the error path must still log after a rollback ([70] lesson).

## Dependencies

- Blocked by: [83] (repository read twins).
- Blocks: [86] (which deletes the sync translation half), [88].

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Frontend untouched; CI green
- [ ] `docs/development.md` layers section: the allowlist sentence
      updated
