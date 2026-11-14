---
title: "[95] Seed tags step on the async services; delete the sync tag-extraction path"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: scripts. No behaviour change.

## Scope

- `database/seed.py`, `cli/backfill_levels.py`,
  `cli/split_merged_concepts.py`, `cli/translate_missing.py` use
  `asyncio.run` on `AsyncSessionLocal`.
- Delete the sync half of `question_translation_service` and the
  remaining sync `concept_service` functions.

- `tests/test_seed.py` forbids AI calls by patching only the **sync**
  seams (`extract_concept_names`, `translate_qa`). When the seed moves
  to the async services, forbid the async seams too, or the "zero AI
  calls" guarantee passes vacuously (found in [93]).

- Done early in [94]: the seed's import step is async and its test
  forbids both sync and async AI seams. Left here: the stored-tags step
  (`apply_seed_extras`, sync `attach_concepts_to_question`,
  `extract_concepts_best_effort`), the three CLIs, the sync
  `translate_missing_languages`.

## Acceptance criteria

- [x] Offline seed still makes zero OpenAI/DeepSeek calls (`test_seed.py`); `test_cli.py` green.

## Dependencies

- Blocked by: [94]
- Blocks: [87]

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

### 2026-11-14 — narrowed and done

**Split on the owner's invitation.** The remaining work was two
independent halves of about [94]'s size each, so this issue keeps the
seed and the tag path, and the `translate_missing` CLI with the sync
translation half moved to [102]. The two re-extract CLIs already run
their AI work async ([91]); their remaining sync bits are read queries
on the CLI's own session, which go with the sync engine in [88].

615 tests pass; ruff and mypy clean; frontend untouched. 4 production
files, 6 test files; 268 lines removed, 117 added.

- **Seed:** import, tag attachment and stored values run in one async
  session (`seed._seed`): stored tags (or extracted ones for an entry
  without) are planned with `async_prepare_concepts_many`, one index for
  every row as in import, then written in one transaction with the
  stored levels and provenance. The seed opens no sync session any
  more.
- **Deleted, no callers left:** `concept_service.extract_concept_names`,
  `attach_concepts_to_question`, `_resolve_sense`, `_new_sense`, the
  dead `translate_missing_name` and `_name_translation_plan`;
  `concept_sense_service.add_term`;
  `question_write_service.extract_concepts_best_effort` and
  `attach_concepts_best_effort`. Concept extraction and matching now
  exist once, async.
- **Added:** `concept_service.async_attach_concepts` (plan, then one
  short write) for single-question callers.
- **Tests:** `conftest.attach_concepts` is a sync bridge for the many
  sync tests that tag rows (as `create_user` is);
  `patch_extract_concept_names` patches the async seam only, since the
  sync one is gone. The prompt and extractor tests drive the real async
  extractor with the chat seam patched. The seed test's guard on the
  deleted sync seam is gone; the async seams stay forbidden.
