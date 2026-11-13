---
title: "[84] Asynchronize concepts: student tag search and the admin tag editor"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], slice 3 of [73]

## Summary

Convert the concepts router (student search plus the admin editor from
[55]) and `concept_sense_service` with its repositories to the async
stack. No change in behaviour.

## Motivation

A self-contained slice: `concepts.py` has ten routes, one service, and
`concept_term_repository` has no other caller, so most of it converts
outright with no twins. It is the smallest of the [73] slices and a
good one to do while [83]'s repository twins are fresh.

## Scope

- Routes in `api/v1/concepts.py`: public `GET /concepts`; admin `GET
  /admin/concepts`, `GET /admin/concepts/{id}`, `PATCH
  /admin/concepts/{id}`, `POST .../terms`, `PATCH .../terms/{term_id}`,
  `DELETE .../terms/{term_id}`, `POST .../merge`, `POST .../split`. The
  `_detail` helper and the `_http_errors` context manager follow.
- `concept_sense_service`: all 27 functions (search, admin list and
  detail, gloss, add/edit/delete term, merge, split, the
  `concept_ids_missing_name` twin from [83] collapses to one function).
- `concept_term_repository` (eleven functions): single caller, convert
  outright.
- `concept_repository`: shared with `concept_service` (extraction and
  matching, used by admin writes and the seed until [85]/[86]) - twins
  for the shared functions, outright for the ones only the sense
  service uses.
- Relationship loads the editor relies on (`Concept.terms`, linked
  questions) become `selectinload` or explicit queries.

## Acceptance criteria

- [ ] All ten routes are `async def` on `get_async_db`.
- [ ] Public search still returns only senses with APPROVED questions
      and a label in `lang`; the admin filters (`all`, `review`,
      `shared`) return the same rows as before.
- [ ] Editor behaviour identical: 409 on a duplicate word after
      normalisation, the oldest word takes over the label on delete,
      merge moves links and words and deletes the source, split moves
      the given questions to a new sense.
- [ ] `tests/test_concept_senses.py` (19 tests) green on `async_db`.

## Out of scope

- The extraction and matching side of `concept_service` ([85], [86]).
- The `split_merged_concepts` CLI: it calls `question_write_service`,
  so it moves with [86].
- Merging the two concept modules into one package ([61], skipped for
  now by the owner).

## Technical notes

Reference: `git diff 260d7c2 9c42cfd -- backend/physics_ai_tutor/services/concept_sense_service.py backend/physics_ai_tutor/repositories/concept_term_repository.py backend/physics_ai_tutor/api/v1/concepts.py`
on `wip/73-async-remaining`. These files had a single caller, so the
WIP version can be taken nearly as is; `concept_repository.py` cannot,
because its WIP version dropped the sync functions `concept_service`
still needs.

## Dependencies

- Blocked by: [83] (for the `concept_ids_missing_name` twin and the
  question-side read twins). Could run in parallel if both sessions
  agree on who adds which twin.
- Blocks: [88].

## Definition of done

- [ ] Backend: `pytest`, `ruff check`, `mypy` pass
- [ ] Frontend untouched; CI green
- [ ] No doc change expected
