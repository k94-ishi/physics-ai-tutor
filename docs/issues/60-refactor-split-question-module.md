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
