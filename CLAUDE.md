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
- build

## Coding Style

- Comments must be one short sentence and written in English.
- Keep functions small.
- Prefer clear naming over clever implementation.