---
title: Golden evaluation set and offline prompt regression check
labels: [feature, ai-review, prompt, testing, backend]
milestone: M4 Partial automation and regression safety
priority: P2
---

**Priority:** P2  **Milestone:** M4 — Partial automation and regression safety

## Summary

Curate a fixed set of human-reviewed questions with expected verdicts, and a
command that runs the current answer prompt and reviewer prompt against it
and reports the change in agreement before a prompt edit is merged.

## Motivation

Prompt edits are currently untested beyond "the tests still pass with a
mocked completion". A golden set turns #15's metric into a gate: a change
that drops reviewer agreement or raises the teacher-reject rate is caught
before students see it. This is also the dataset that makes the project's
evaluation story concrete.

## Scope

- `backend/eval/golden.jsonl`: 50–100 rows exported via #11 and hand-checked
  by a teacher; balanced across approve / edit / reject and reason codes;
  both languages.
- `uv run python -m physics_ai_tutor.cli.eval_prompts --set eval/golden.jsonl`:
  regenerates answers (optional, costs API calls), runs the reviewer, prints
  the #15 tables and a one-line verdict against stored baselines.
- Baselines committed as `eval/baseline-<prompt_version>.json`.
- CI: not on every PR (cost); a manual `workflow_dispatch` job with the API
  keys as secrets, required before merging changes to `core/prompts.py`
  (document the rule in `AGENTS.md`).

## Acceptance criteria

- [ ] Running the command twice on the same prompt version gives the same
      summary within noise (set temperature 0 for eval runs).
- [ ] A deliberately broken prompt (e.g. remove the formatting rules) is
      flagged by the comparison.

## Out of scope

- Fully automatic gating on every PR.

## Technical notes

Put eval rows through the same code path as production (`rag_service` /
`deepseek_service`), only with a fixed seed/temperature where the API
allows it.

## Dependencies

- Blocked by: #11, #13, #15
- Blocks: #18, #19, #20

## Definition of done

- [ ] Backend checks pass; the command has a dry-run mode that needs no API key
- [ ] `AGENTS.md` and `docs/development.md` describe when to run it
