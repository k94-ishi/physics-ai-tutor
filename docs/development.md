# Development Guide

## Prerequisites
- Python 3.13
- uv
- Node.js 24 (see `frontend/.nvmrc`)
- Docker / Docker Compose

## Git Clone

```bash
git clone https://github.com/k94-ishi/physics-ai-tutor.git
cd physics-ai-tutor
```

## Docker compose

### Build and start all services

```bash
# build & start
docker compose up -d --build

# stop
docker compose down

# start
docker compose up -d
```

### Setup DB

```bash
# Database Migration
docker compose exec backend uv run alembic upgrade head
```

### Seed data

The project includes sample physics questions for local development.

To load sample data:

```bash
docker compose exec backend uv run python -m physics_ai_tutor.database.seed
```

The seed script reads `backend/physics_ai_tutor/database/seed.json` and
inserts every entry as an approved question. It generates embeddings and
extracts concepts, so `OPENAI_API_KEY` and `DEEPSEEK_API_KEY` must be set.
The import is all-or-nothing: if any question text already exists, nothing
is inserted. Reset the database (see [docs/database.md](database.md)) before
re-seeding.

`seed.jsonl` in the same directory holds the same data in JSONL form, which
is the format accepted by the admin "Upload" page.

### Create an admin user

There is no sign-up page. Create the first admin from the CLI:

```bash
docker compose exec backend uv run python -m physics_ai_tutor.cli.create_user \
  --email admin@example.com --role admin
```

You will be prompted for a password (8 to 128 characters). Then log in at
`http://localhost:3000/login`.

### Access

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000/docs`

## Database Management

The schema, migration history, and migration workflow are documented in
[docs/database.md](database.md).

```bash
# Show applied revision
docker compose exec backend uv run alembic current

# Create Migration (review the generated file before committing)
docker compose exec backend uv run alembic revision --autogenerate -m "description"

# Apply Migration
docker compose exec backend uv run alembic upgrade head

# Roll back one revision
docker compose exec backend uv run alembic downgrade -1
```

Every schema change must ship with a migration. Do not use `init_db.py` on a
database you intend to migrate.

## Testing

### Backend

Run from the `backend/` directory. Tests need the `postgres-test` container
(port 5433) started by Docker Compose. The suite wipes the test database,
rebuilds it with Alembic, and truncates tables between tests; OpenAI and
DeepSeek calls are mocked. Set `TEST_DATABASE_URL` to a database nobody else
uses if the container is shared (see
[docs/database.md](database.md#test-database-behaviour)).

```bash
cd backend
uv sync
uv run pytest
uv run ruff check .
uv run mypy .
```

Or inside the container:

```bash
docker compose exec backend uv run pytest
```

### Frontend

Run from the `frontend/` directory.

```bash
cd frontend
npm ci
npm run lint
npx tsc --noEmit
npm run build
```

## CI/CD

- GitHub Actions (`.github/workflows/ci.yml`) runs on pull requests to
  `main`: backend migrations, ruff, mypy, pytest against a pgvector
  container, and frontend lint, type check, and build.
- Frontend is deployed to Vercel, backend to Render, database on Supabase.
- Apply migrations to production (`alembic upgrade head` with the Supabase
  `DATABASE_URL`) before deploying backend code that needs the new schema.

## Environment Variables

Copy the templates and fill in the values. Do this before `docker compose up`,
because both containers load these files.

```bash
cp backend/.env.template backend/.env
cp frontend/.env.template frontend/.env.local
```

Backend (`backend/.env`):

| Variable | Required | Notes |
| --- | --- | --- |
| `DATABASE_URL` | yes | `postgresql+psycopg://physics:physics@postgres:5432/physics_ai_tutor` inside Docker, `localhost:5432` from the host |
| `OPENAI_API_KEY` | yes | Embeddings (`text-embedding-3-small`) |
| `DEEPSEEK_API_KEY` | yes | Answer generation and concept extraction |
| `JWT_SECRET_KEY` | yes | Generate with `openssl rand -base64 32` |
| `JWT_ALGORITHM` | yes | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | yes | e.g. `15` |
| `JWT_REFRESH_THRESHOLD_MINUTES` | no | Default `10` |
| `ENVIRONMENT` | no | `development` enables `/docs`; anything else disables it |
| `BACKEND_CORS_ORIGINS` | no | JSON list of allowed origins |
| `COOKIE_SECURE` | no | `true` in production (HTTPS only) |
| `SAME_SITE` | no | `lax`, `strict`, or `none` |
| `EMBEDDING_MODEL`, `DEEPSEEK_CHAT_MODEL`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MAX_TOKENS` | no | Model overrides, see `core/config.py` |
| `TRUST_FORWARDED_FOR` | no | Use `X-Forwarded-For` for rate limiting (default `true`) |

Frontend (`frontend/.env.local`):

| Variable | Notes |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | Backend URL used by the browser, e.g. `http://localhost:8000` |
| `INTERNAL_API_URL` | Backend URL used by server-side rendering inside Docker, e.g. `http://backend:8000` |

## Pull Request Checks

Before creating a pull request:

```bash
# Backend
uv run pytest
uv run ruff check .
uv run mypy .

# Frontend
npm run lint
npx tsc --noEmit
npm run build
```

## Further Reading

- [docs/database.md](database.md): schema, Alembic migrations, seed data
- [docs/api.md](api.md): endpoint reference and access rules
- [docs/security.md](security.md): security model and dependency policy
- [AGENTS.md](../AGENTS.md): project rules for contributors and coding agents
