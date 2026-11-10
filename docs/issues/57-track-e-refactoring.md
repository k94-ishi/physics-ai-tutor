---
title: "[57] Track E: refactoring after the November feature burst"
labels: [epic, roadmap, refactor]
milestone: M1 Student value
priority: P1
---

**Priority:** P1  **Milestone:** M1 — Student value

Owner's request (2026-11-10): the structure grew complicated after many
features; review it and plan a refactor. No behaviour change is intended
anywhere in this track: every step must keep the API, the database and
the screens identical, and the existing tests are the safety net.

## Review findings (2026-11-10, measured on commit 02a5604)

| Area | Finding | Evidence |
| --- | --- | --- |
| Backend layering | AGENTS.md asks for router/service/repository separation; 3 routers query the DB or a repository directly | 8 `db.*` calls in `api/v1/concepts.py`, 2 in `admin.py`, 2 in `ai.py`; repositories imported in `concepts.py`, `questions.py`, `users.py` |
| Backend size | Two "god" modules | `question_service.py` 818 lines (create, list, review, translate, embed, concepts, bulk), `api/v1/questions.py` 649 lines |
| Long functions | 8 functions over 60 lines; AGENTS.md says keep functions small | `get_related_questions` 127, `ask_ai` 101, `get_prerequisites` 97, `review_question` 83 |
| Two concept modules | Responsibilities overlap and import each other | `concept_service` (extraction, matching, translation) and `concept_sense_service` (terms, search, admin) |
| Duplicated helpers | Same rule written several times | text normalisation x3 (`concept_repository.normalize`, `concept_sense_service.normalize_term`, `embedding_service.normalize_query`); `"<ja> \| <en>"` pair text x3; `_is_admin` inline in 2 routers |
| Language plumbing | `[53]` added a `strict_language` flag plus `missing_language_ids` out-parameters threaded through 4 call chains | `prepare_for_response`, recommendation and prerequisite services, router |
| Transactions | Commits are scattered over services and repositories | 20 `db.commit()` in 7 services, 2 in a repository |
| Legacy | `concepts.name_ja/name_en` mirrors still read by 9 modules ([55] stage 5 pending) | |
| Frontend size | One admin page holds most of the admin UI | `admin/questions/page.tsx` 1,398 lines, 21 `useState` |
| Frontend duplication | Same patterns hand-copied | request-id race guard in 5 components; preview-card markup in 2; `api.ts` 586 lines, 42 functions in one file |
| i18n | One 1,196-line table for every page | `translations.ts` |
| Tests | Backend suite takes ~9 min; 7 tests each seed all 144 questions | `tests/test_cli.py` |
| Docs | `CLAUDE.md` is a stale copy of `AGENTS.md` (no prompt rules, no vitest), although README says it links to AGENTS.md | |

What is in good shape and should stay: the Alembic chain, the prompt
library + fingerprint tests, the strict-language rule itself, the
reproducible seed, and the test coverage of behaviour.

## Order (each step is a separate, independently mergeable PR)

Revised 2026-11-10 after [58]: test speed comes right after the quick
wins (every later step runs the suite many times), and comment style is
its own issue, applied as files are touched.

1. ~~[58] quick wins~~ done 2026-11-10
2. ~~[66] test suite speed~~ done 2026-11-11 (5:56 -> 0:38)
3. [59] backend layering: routers call services only; one place commits - **next up**
4. [60] split `question_service` and `api/v1/questions.py` by use case
5. [61] concept domain: one `services/concepts/` package; legacy name columns removed ([55] stage 5)
6. [62] language resolution as one response step instead of flags
7. [63] frontend: shared hooks and card components; split the admin queue page
8. [64] frontend: split `api.ts` and `translations.ts` by feature
- Alongside 3-8: [65] English one-sentence comments (166 Japanese comment
  lines, 70 multi-line docstrings); the CI check lands first.

Naming (owner, 2026-11-10): "concept" in all code; "tag" only on screen.

Other open issues reviewed on 2026-11-10:

- [44] the owner's decision is in its Log (2026-11-03) and no label
  changed, so nothing is left but closing it - owner to confirm.
- [20] describes prompts in `core/prompts.py`; since [24] the texts live in
  `prompt_library.yaml`. Update the design when it is picked up.
- [21] /help should say "tag" and explain the "which meaning?" chooser.
- [00] roadmap was last revised 2026-10-28; the tracks [45]-[48], [57]
  carry the current order. Refresh or mark as historical.
- [23] (privacy debt) is still open in Track C; independent of [57].

Rules for the whole track:

- No new features inside a refactor PR; behaviour changes get their own issue.
- Before each PR: pytest, ruff, mypy, lint, tsc, vitest, build (AGENTS.md).
- Refactor in small moves with tests green after each commit; prefer
  moving code to rewriting it.
- [61] is the only step with a migration; it runs after [54] has rolled
  the tag tables out to production, so production never has to skip a
  schema version.
