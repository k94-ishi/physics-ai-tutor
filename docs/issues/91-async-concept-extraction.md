---
title: "[91] Asynchronize concept extraction and the re-extract route"
labels: [backend, async, refactor]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value  **Track:** [67], part of [73]

## Summary

One small slice of [73]: concept extraction seam. No behaviour change.

## Scope

- Route `POST /questions/concepts/extract`.
- `question_write_service.reextract_concepts_for_questions`,
  `extract_concepts_best_effort`, `attach_concepts_best_effort` and the
  extraction/matching path of `concept_service` (async twins; the seed
  and create still use sync until [93]/[95]).
- Left over from [90]: `concept_term_repository.senses_by_words`, the sync
  `get_many`, the sync `concept_sense_service.add_term`, and the dead
  `senses_with_any_term`.
- Prepare (LLM call, no session) then apply (short transaction); remove
  `reextract_concepts_for_questions` from the [82] allowlist.

## Acceptance criteria

- [x] Re-extract tests green; a runtime probe shows no open transaction during extraction.

## Dependencies

- Blocked by: [90]
- Blocks: [85]

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

## Log

### 2026-11-13 — done

603 tests pass (602 + 1 new probe); ruff and mypy clean; frontend
untouched. 9 production files, 6 test files.

**The [82] shape.** Re-extracting one question is now four steps: read
the question (short transaction), call DeepSeek for the tag names (no
transaction), read the matching senses (short transaction) and work out
any embeddings (no transaction), then delete the old links and write
the new ones (one short transaction). Before, the DeepSeek call and the
embedding calls all ran inside one transaction. The lexical allowlist in
`test_architecture.py` lost `reextract_concepts_for_questions`, and
`test_llm_connection_discipline.py` has a new probe that records
`in_transaction()` at both AI calls.

**One matching rule, two executors.** Create, review and the seed still
use the sync `attach_concepts_to_question` until [85]/[93]/[95]. The
rule itself (`_candidates`, `_choose`, `_parse_names`) is now shared,
and the async side plans before it writes: `async_prepare_concepts`
returns `PlannedSense` objects, `async_apply_concepts` writes them. Two
details keep the plan identical to the sync behaviour:

- A sense planned but not saved yet has no id, so candidates are keyed
  by object identity, and such a sense takes later aliases at once
  (`add_unsaved_term`).
- An alias planned for an existing sense is recorded as pending, so a
  later pair of the same question sees it, as it would after the sync
  code's immediate write.

**Callers.** The route is async. `backfill_levels` and
`split_merged_concepts` drive the async use case with `asyncio.run` on
their own `AsyncSessionLocal`; the rest of each CLI is unchanged until
[95].

**Tests.** The three re-extract tests are async. `conftest` gained
`patch_extract_concept_names`, which patches both seams (the autouse
mock uses it too). The two CLI tests now patch both seams and point the
CLI's async session at the test database. Without that they passed
here only because the local `DATABASE_URL` happened to be the test
database; in CI they would have written to the wrong one.

**Cleanup from [90].** `senses_with_any_term` had no caller and is
deleted. `concept_term_repository.senses_by_words`, its sync `get_many`
and the sync `concept_sense_service.add_term` stay: create, review and
the seed still use them.
