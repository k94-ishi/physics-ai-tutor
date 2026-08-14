# Physics AI Tutor - Claude Code Instructions

## Project Overview

Physics AI Tutor is an educational web application for Japanese high school physics students.

The long-term goal is an AI-assisted tutoring system using RAG and LLMs.

Current phase:
- Build a solid web application without AI features first.
- Complete CRUD-based question management.
- Prepare the foundation for future RAG integration.

---

## Tech Stack

### Backend
- Python
- FastAPI
- SQLAlchemy ORM
- PostgreSQL
- Pydantic

Architecture:

Router
  ↓
Service
  ↓
Repository
  ↓
Database


### Frontend
- Next.js (App Router)
- TypeScript
- React
- Tailwind CSS

---

## Current Features

Implemented:
- Question list API
- Question detail API
- Create question API
- Bulk question registration API
- Update question API
- Delete question API
- Admin question management page

Working on:
- UI improvement
- Category management
- Search functionality

---

## Development Principles

### Backend

- Keep separation of concerns:
  - Router handles HTTP concerns.
  - Service handles business logic.
  - Repository handles database operations.

- Do not put FastAPI-specific logic inside Service or Repository.

- Use SQLAlchemy ORM.

- Use Pydantic schemas for API input/output.

- Prefer clear and maintainable code over premature abstraction.

---

### Frontend

- Use Next.js App Router conventions.

- Prefer functional components and React hooks.

- Keep components simple.

- Avoid unnecessary abstraction.

- Use TypeScript types explicitly for API communication.

- Follow React 19 conventions.

---

## UI Development Guidelines

When modifying UI:

- Prioritize usability over visual complexity.
- Use Tailwind CSS.
- Keep the design clean and professional.
- Make the application suitable for a portfolio project.

Focus on:
- Clear navigation
- Good spacing
- Readable forms
- Proper loading/error states

Avoid:
- Overly complex animations
- Unnecessary dependencies

---

## Coding Style

- Write code that is easy for other engineers to understand.
- Add comments only when the reason is not obvious.
- Prefer small focused functions.
- Avoid duplicated logic when it becomes meaningful.

---

## Git Workflow

Make small meaningful commits.

Examples:

- Add question edit page
- Improve admin UI
- Add category model
- Implement search API

---

## Future Roadmap

Future features:

1. Authentication
   - JWT based admin authentication

2. Categories
   - Physics topic management

3. Search
   - Keyword based question search

4. RAG
   - Embedding generation
   - Vector search with pgvector
   - Similar question retrieval

5. LLM Integration
   - Generate answers for unknown questions

6. AI Review Workflow
   - Store generated answers separately
   - Human review
   - Approve / Reject / Hold
   - Promote approved content to knowledge base

---

## Important

Do not implement AI features unless explicitly requested.

The current priority is:
1. Finish the web application.
2. Improve maintainability.
3. Deploy a working version.
4. Add AI features incrementally.