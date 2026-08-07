# Physics AI Tutor

I worked as a high school physics teacher in Japan for three years. During that time, I realized that many students struggled not only with understanding physics but also with formulating the questions they wanted to ask.

This project aims to help students by suggesting possible questions, providing clear explanations, and eventually offering AI-assisted learning support.

The project is still in its early stages, but it is being developed into a full-stack AI tutoring application.

## Features

- Question management (CRUD)
- Admin dashboard
- RESTful API with FastAPI
- PostgreSQL database
- Next.js frontend
- Only Japanese language

## Architecture

```text
Next.js
    │
FastAPI
    │
PostgreSQL
```

## Setup

- Start containers:

```bash
docker compose up --build
```

- Initialize DB

```bash
docker compose exec backend uv run python -m physics_ai_tutor.database.init_db
docker compose exec backend uv run python -m physics_ai_tutor.database.seed
```

- Access:
  - Frontend: http://localhost:3000
  - API Docs: http://localhost:8000/docs

## Planned Features

- Category management
- Keyword search
- JWT authentication
- RAG (Retrieval-Augmented Generation)
- Embedding-based similarity search
- AI-generated answers with human review
- English version
- Manim animation integration for physics explanations