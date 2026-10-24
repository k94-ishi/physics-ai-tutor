# Backend

FastAPI backend of Physics AI Tutor.

- Project overview: [../README.md](../README.md)
- Local setup and testing: [../docs/development.md](../docs/development.md)
- Database schema and migrations: [../docs/database.md](../docs/database.md)
- API reference: [../docs/api.md](../docs/api.md)

## Layout

```
physics_ai_tutor/
├── api/            # FastAPI routers (v1) and auth dependencies
├── core/           # Settings, JWT, logging, rate limiting, LLM clients
├── database/       # Engine, session, seed script
├── models/         # SQLAlchemy models
├── repositories/   # Database access
├── schemas/        # Pydantic request/response models
├── services/       # Business logic (RAG, embeddings, review, recommendations)
└── cli/            # Management commands (create_user)
alembic/            # Migrations
tests/              # pytest suite
```
