---
title: "[60] Split question_service and api/v1/questions.py by use case"
labels: [refactor, backend]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [57]

## Summary

`question_service.py` (818 lines) and `api/v1/questions.py` (649 lines)
hold every question use case. Split them along the lines the docs already
use, keeping public function names as re-exports for one release.

## Proposed modules

| New module | Moves there |
| --- | --- |
| `services/questions/reading.py` | list, detail, exact match, response preparation |
| `services/questions/authoring.py` | create, update, delete, import, bulk delete |
| `services/questions/review.py` | review, bulk review, EDIT_APPROVE diff |
| `services/questions/translation.py` | translate missing, machine-counterpart refresh, embeddings per language |
| `api/v1/questions.py` | public reads only |
| `api/v1/admin_questions.py` | admin writes, review, import, bulk, translate, extract |

Also break up the long functions: `get_related_questions` (127 lines:
candidate gathering, scoring, language filter), `get_prerequisites` (97),
`review_question` (83), `fetch_questions` (70).

## Acceptance criteria

- [ ] No module over ~350 lines, no function over ~50 lines in the moved code.
- [ ] URL paths and OpenAPI schema unchanged (compare `/openapi.json` before/after).
- [ ] All checks pass.

## Dependencies

- Blocked by: [59]

## Log

### 2026-11-11 - done

- `services/question_service.py` (776 lines, 30 functions) -> five modules
  of 111-321 lines: `question_presentation_service`, `question_read_service`,
  `question_write_service`, `question_review_service`,
  `question_translation_service`. Flat `*_service.py` names, matching the
  rest of `services/`. Five shared helpers became public (`embed_language`,
  `translate_into`, `translate_missing`, `refresh_machine_translations`,
  `attach_concepts_best_effort`).
- **Moved, not rewritten**: an AST comparison shows all 30 function bodies
  identical to the originals (apart from those five names).
- **No re-export layer**: every caller imports the module it uses (the
  issue had suggested re-exports for one release; with only one test
  monkeypatching the old module, explicit imports were cheaper and keep
  patching reliable - patching a re-export does not reach the real call).
- `api/v1/questions.py` (652) -> public reads (315) + `admin_questions.py`
  (375), registered after it under the same prefix.
- Long functions broken up, same order of operations: `get_related_questions`
  127 -> 30 lines + 4 helpers (tie order unchanged: the candidate set is
  built by the same expression); `get_prerequisites` 97 -> 25 + 5 helpers;
  `review_question` 83 -> 45 + 3 helpers.
- **Behaviour checks**: OpenAPI schema byte-identical; the same 49 routes,
  and no route can shadow another in either version's matching order
  (FastAPI matches in registration order, so the router split could have
  changed which route answers a request).
- Checks: pytest 525 (~40 s), ruff, ruff format, mypy.

Not done here, listed for later:

- `fetch_questions` is still 52 lines: 16 filter parameters passed twice
  (list and count). The fix is a typed filter object shared by router,
  service and repository - a signature change across three layers, best
  done with [62].
- Functions over 50 lines outside this issue: `review_question_with_outcome`
  (67, AI review), `get_current_user` (65, auth), `review_pending.main` (60, CLI).
