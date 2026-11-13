---
title: "[85] Asynchronize the review routes: review, bulk review, history"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: teacher review actions. No behaviour change.

## Scope

- Routes `GET /questions/{id}/reviews`, `POST /questions/{id}/review`,
  `POST /questions/bulk-review`.
- `question_review_service` and `question_review_repository` (outright).
- Async twins of `refresh_machine_translations` / `embed_language` for
  edit-approve; approve uses the async extraction from [91].

## Acceptance criteria

- [x] Review rows identical (action, reason, language, before/after); `test_review_workflow.py` and `test_review_reasons.py` green.

## Dependencies

- Blocked by: [91]
- Blocks: [92]

## Log

### 2026-11-13 — re-scoped smaller

Owner found [83] (22 files, 35 tests) too big. The earlier, wider version of this issue was split; see [73]'s table.

## Rules (all [73] slices)

- Twins only while an unconverted caller needs the sync version; delete a
  sync function in the slice that removes its last caller.
- Tests that call converted code are async on `async_db`; arrange with
  `db` and commit. Frontend untouched.
- Reference production code: `git diff 260d7c2 9c42cfd -- <paths>` on
  `wip/73-async-remaining` (its twins are collapsed; adapt, do not copy).

## Definition of done

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] Log entry in this file; `status.md`, [67] and [73] updated

### 2026-11-13 — done

605 tests pass (603 + 2 new); ruff and mypy clean; frontend untouched.
4 production files, 6 test files.

**Bigger than the scope said.** The sync review held one transaction
across up to four kinds of AI call: re-embedding an edited text,
refreshing machine translations, concept extraction on approve, and
translating a missing language. The [82] tripwire never saw it because
each call sat one or two hops away. The review now runs as:

1. read the question (short transaction);
2. every AI call on a **detached draft** copy, with no transaction open;
3. one short transaction: text, embeddings, translations, status,
   concepts and levels, the review row, and the admin response fields.

The draft matters for bulk review: the same session goes on to the next
question, so a failed AI call must not leave a half-edited row in it.
Failure rules are unchanged: an embedding failure on edit-approve
writes nothing; a failed extraction or translation is skipped.

**Routes and code.** `GET /questions/{id}/reviews`,
`POST /questions/{id}/review` and `POST /questions/bulk-review` are
async. `question_review_service` exists only in async form;
`question_review_repository.create` and `list_for_question` are async
only; `list_with_questions_since` stays sync for the export ([96]).
`question_repository.async_update_status` was added.

**Tests.** 11 review tests moved to `async_db`; the extraction spy
patches both seams. Two new tests: a runtime probe that embedding,
translation and extraction during an edit-approve all run with no
transaction, and a test that a failed edit-approve leaves the row, the
history and the session untouched.

Three tests needed setup fixes, not behaviour changes, because the
route no longer shares the test's session:

- one recommendation test reviewed a row it had flushed but not
  committed;
- the difficulty-levels fixture mocked only the sync extraction;
- a review-metrics test inserted its "later" AI verdict in a
  transaction opened before the human review. PostgreSQL's `now()` is
  the transaction's start time, so the verdict was stamped earlier than
  the review. The test now commits first.

**Test database clash.** Another session in the `oak` worktree was
running its suite on the same test database name
(`physics_ai_tutor_test_oak83`), so two of this slice's runs were
refused by the suite's lock. That process was left alone; this
session now uses its own database name.

**Found while answering the owner:** concept matching re-embeds every
candidate sense's words on each ambiguous extraction, although each
sense already has a stored vector. Filed as [100]; not changed here.
