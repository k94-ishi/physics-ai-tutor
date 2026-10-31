# AGENTS.md

## Project Overview

Physics AI Tutor is a RAG-based physics learning platform basically for high school students.

## Architecture Principles

- Prefer existing verified QA over LLM generation.
- Avoid unnecessary LLM API calls.
- Keep educational content reviewable.

## Backend Rules

- FastAPI + SQLAlchemy
- Use repository/service/router separation.
- Add Alembic migration for DB schema changes.
- Never modify production DB directly.

## Frontend Rules

- Next.js App Router
- Use TypeScript strictly.
- Keep components reusable.

## Database Rules

- Never modify schema without migration.
- Keep seed data reproducible.

## Testing Requirements

Before commit:

Backend:
- pytest
- ruff
- mypy

Frontend:
- lint
- tsc
- vitest (`npm test`)
- build

See docs/development.md (Testing) for layout and conventions.

## Prompt Rules

- Every LLM prompt text lives in `backend/physics_ai_tutor/core/prompt_library.yaml`
  (a list of records: family, name, language, version, description, text; prose in block scalars),
  never inline in Python. Render it readably with
  `uv run python -m physics_ai_tutor.cli.show_prompts`.
- Anything a student reads must exist in both Japanese and English and be
  selected by the request language. Machine-processing prompts (translation,
  concept extraction) may keep one English instruction so the output format
  stays identical, but must carry language-matched worked examples and the
  bilingual glossary.
- Changing any text in a family requires bumping that family's `version` in
  the YAML and recording the new fingerprint in
  `backend/tests/test_prompts.py`; the suite fails otherwise.
- Before merging a change to the `answer` or `ai_review` families, run the
  prompt eval (`uv run python -m physics_ai_tutor.cli.eval_prompts`, or the
  "Prompt Eval" GitHub Actions workflow) against `backend/eval/golden.jsonl`
  and update the committed baseline if the change is intended.

## Coding Style

- Comments must be one short sentence and written in English.
- Keep functions small.
- Prefer clear naming over clever implementation.