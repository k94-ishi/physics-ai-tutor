# Development Guide

## Prerequisites
- Python 3.13
- uv
- Node.js
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

The seed data source is located at: `backend/physics_ai_tutor/database/seed.jsonl`

You can add or modify sample questions if needed.

### Access

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000/docs`

## Database Management

```bash
# Create Migration
docker compose exec backend uv run alembic revision --autogenerate -m "description"

# Apply Migration
docker compose exec backend uv run alembic upgrade head
```

## Testing

### Backend

```bash
uv run pytest
uv run ruff check .
uv run mypy .
```

### Frontend

```
npm run lint
npx tsc --noEmit
npm run build
```

## CI/CD

- GitHub Actions workflow
- Vercel deployment
- Render deployment

## Environment Variables

Copy the template and fill in the values:

```bash
cp backend/.env.template backend/.env
```

Backend:
- DATABASE_URL
- OpenAI API key
- DeepSeek API key
- JWT secret key

Generate a random JWT secret key:

```bash
openssl rand -base64 32
```

Frontend:
- NEXT_PUBLIC_API_URL

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
