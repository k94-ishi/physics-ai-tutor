# Physics AI Tutor

Physics AI Tutor is an AI-assisted learning platform for high school physics students.

I worked as a high school physics teacher in Japan for three years. During that time, I realized that many students struggled not only with understanding physics concepts but also with formulating the questions they wanted to ask.

This project aims to support students by organizing physics knowledge, helping them find relevant explanations, and eventually providing AI-powered tutoring through Retrieval-Augmented Generation (RAG).

The application is currently under active development as a full-stack AI tutoring system.

---

## Demo

https://physics-ai-tutor-blue.vercel.app/

----

## Features

### Question Management

- Create, read, update, and delete physics questions and answers
- Admin dashboard for managing educational content
- Pagination and keyword-based search

### Authentication and Authorization

- JWT-based authentication with HttpOnly cookies
- Role-based access control
- Admin-only content management operations
- User management API

### Semantic Search

- Generate question embeddings using OpenAI embedding models
- Store embeddings in PostgreSQL with pgvector
- Search similar questions using cosine similarity

### Backend

- RESTful API with FastAPI
- SQLAlchemy ORM
- Repository / Service / Router architecture
- Database migration with Alembic
- Automated tests with pytest

### Frontend

- Next.js (App Router)
- React + TypeScript
- Responsive UI for question browsing and administration

---

## Architecture

```text
                 Next.js
                    |
                    |
                 FastAPI
                    |
          ---------------------
          |                   |
     PostgreSQL          OpenAI API
          |
       pgvector
```

Current AI pipeline:

```text
User Question

      |
      v

Embedding Generation
(OpenAI text-embedding-3-small)

      |
      v

Vector Similarity Search
(PostgreSQL + pgvector)

      |
      v

Relevant Questions
```

Future RAG pipeline:

```text
User Question

      |
      v

Vector Search

      |
      v

Context Retrieval

      |
      v

LLM Generation

      |
      v

AI Tutor Response
```

---

## Tech Stack

### Backend

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- pgvector
- Alembic
- pytest

### Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS

### Infrastructure

- Docker Compose
- Vercel (Frontend)
- Render (Backend)
- Supabase PostgreSQL (Production Database)

### AI

- OpenAI Embedding API (`text-embedding-3-small`)
- DeepSeek API (planned for LLM response generation)

---

## Local Development

### Start containers

```bash
docker compose up --build
```

### Initialize database

```bash
docker compose exec backend uv run alembic upgrade head
docker compose exec backend uv run python -m physics_ai_tutor.database.seed
```

### Access

- Frontend:
  http://localhost:3000

- API Documentation:
  http://localhost:8000/docs

---

## Testing

Backend tests:

```bash
uv run pytest
```

Current status:

- Backend: 100+ tests passing
- Frontend: build, typecheck, and lint passing

---

## Deployment

Production deployment is planned with:

```text
Frontend
  |
  v
Vercel

Backend
  |
  v
Render

Database
  |
  v
Supabase PostgreSQL
```

The production demo will be available at:

```
https://ai-tutor.pencil-net.com
```

## Redister first admin

```bash
uv run python -m physics_ai_tutor.cli.create_user \
  --email admin@example.com \
  --role admin

# Enter password interactively
```

---

## Roadmap

- [x] Question management API
- [x] Admin dashboard
- [x] Pagination and keyword search
- [x] JWT authentication
- [x] Role-based authorization
- [x] Embedding generation
- [x] Similar question search using pgvector
- [x] Production deployment
- [ ] RAG-based AI answer generation
- [ ] DeepSeek LLM integration
- [ ] AI-generated answer review workflow
- [ ] Student-facing question submission flow

### Future

- [ ] English version
- [ ] Human-in-the-loop knowledge management
- [ ] AI-generated educational content pipeline

## License

This project is licensed under the MIT License.
