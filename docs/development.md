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
inserts every entry as an approved question in both languages. Entries may
be `{"question", "answer"}` (Japanese, English machine translated) or carry
explicit `question_ja` / `answer_ja` / `question_en` / `answer_en` columns
(a supplied English text is kept as a human translation). It generates
embeddings, extracts concepts and translates, so `OPENAI_API_KEY` and
`DEEPSEEK_API_KEY` must be set.
The import is all-or-nothing: if any question text already exists, nothing
is inserted. Reset the database (see [docs/database.md](database.md)) before
re-seeding.

`seed.jsonl` in the same directory holds the same data in JSONL form, which
is the format accepted by the admin "Upload" page.

### Translate existing rows

Rows that only have one language (for example data created before the
bilingual schema) can be filled by machine translation:

```bash
docker compose exec backend uv run python -m physics_ai_tutor.cli.translate_missing --dry-run
docker compose exec backend uv run python -m physics_ai_tutor.cli.translate_missing
```

Terminology used by the translator and the English prompts comes from
`GLOSSARY` in `backend/physics_ai_tutor/core/prompts.py`; add project terms
there (Japanese to English).

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

Both halves of the project have automated suites and CI runs them on every
pull request. Run them locally before pushing.

### Backend (pytest)

Run from the `backend/` directory. Tests need the `postgres-test` container
(port 5433) started by Docker Compose; OpenAI and DeepSeek calls are mocked.

```bash
cd backend
uv sync
uv run pytest                 # whole suite
uv run pytest tests/test_questions.py -k review   # one file / pattern
uv run pytest --cov           # with coverage report
uv run ruff check .
uv run mypy .
```

Or inside the container:

```bash
docker compose exec backend uv run pytest
```

How the database is handled:

- Each checkout gets its own auto-created test database
  (`physics_ai_tutor_test_<hash>` derived from the path), so several
  worktrees can share one `postgres-test` container. Set `TEST_DATABASE_URL`
  to override.
- The schema is built once per session with `alembic upgrade head` and
  tables are truncated between tests, so model/migration drift fails the
  suite (`tests/test_migrations.py`).
- A PostgreSQL advisory lock is held for the session; a second concurrent
  run on the same database aborts immediately instead of corrupting it.

Layout of `backend/tests/`:

| File | Covers |
| --- | --- |
| `conftest.py` | Database lifecycle, `client` / `admin_client` / `user_client` fixtures, mocks for embeddings and concept extraction |
| `test_questions.py`, `test_users.py`, `test_auth.py`, `test_ai.py`, `test_health.py` | HTTP API, one file per router: status codes, auth rules, validation |
| `test_rate_limit.py` | Postgres-backed rate limiter: window counting, pruning, check/record split |
| `test_review_workflow.py` | End-to-end review flow: AI answer saved as unreviewed, hidden from students, approved / edited / rejected by an admin, history recorded |
| `test_*_service.py` | Service layer: RAG context, embeddings, concepts, recommendations, question lifecycle |
| `test_*_repository.py` | Repository queries against a real PostgreSQL + pgvector |
| `test_models.py` | Column defaults, cascades |
| `test_migrations.py` | Single Alembic head, models match migrations |
| `test_cli.py` | `create_user` and `translate_missing` CLIs and the seed script |
| `test_language.py` | Bilingual rows: eager translation, provenance, `lang` resolution, English ask flow, cache tiers, review in either language, translate endpoint, import shapes |
| `test_logging.py` | Request logging middleware |

Conventions:

- API tests use the `client` fixtures and assert on HTTP responses; service
  and repository tests take the `db` session directly.
- Anything that calls OpenAI or DeepSeek must be mocked. `conftest.py`
  already patches `embedding_service.create_embeddings`,
  `concept_service.extract_concept_names` and
  `translation_service.translate_qa` (which returns `"[en] <text>"` style
  markers so tests can assert on translations); patch `deepseek_service`
  per test.
- Admin-only endpoints need a test for `admin_client` (success),
  `user_client` (403) and `client` (401).
- Any endpoint that returns question content needs a test proving
  non-admins only see `APPROVED` rows.

### Frontend (Vitest + Testing Library)

Run from the `frontend/` directory. Tests run in jsdom with no backend;
`fetch` and `next/navigation` are mocked where needed.

```bash
cd frontend
npm ci
npm test                      # single run (used in CI)
npm run test:watch            # watch mode
npm run test:coverage         # coverage report in coverage/
npm run lint
npx tsc --noEmit
npm run build
```

Configuration lives in `frontend/vitest.config.mts` and
`frontend/vitest.setup.ts` (jest-dom matchers, automatic cleanup, a
`localStorage` polyfill, and `NEXT_PUBLIC_API_URL=http://api.test`).

Test files sit next to the code in `__tests__/` folders and end in
`.test.ts` / `.test.tsx`:

| Location | Covers |
| --- | --- |
| `src/lib/__tests__/api.test.ts` | Request building (query params, JSON bodies, multipart), cookie inclusion, `ApiError` on non-2xx, 204 handling |
| `src/lib/__tests__/markdown.test.ts` | LaTeX delimiter normalisation for DeepSeek output |
| `src/lib/__tests__/concurrency.test.ts` | Concurrency limiter used by bulk admin actions |
| `src/lib/hooks/__tests__/useQueryState.test.tsx` | URL-backed list state (defaults omitted, `router.replace` without scroll) |
| `src/lib/i18n/__tests__/` | Translation tables have identical keys and placeholders in `ja` and `en`; language switching, persistence, `<html lang>` |
| `src/lib/auth/__tests__/AuthContext.test.tsx` | Session bootstrap, 401 treated as logged out, login / logout state |
| `src/components/ui/__tests__/` | `Pagination`, `StatusMessage`, `ConfirmDialog`: rendering, accessibility roles, callbacks, keyboard handling |

Conventions:

- Wrap components in `LanguageProvider` and query by role and visible text
  (Japanese, the default language) rather than by CSS class.
- Mock `@/lib/api` with `vi.mock` for components that load data; mock
  `fetch` only in `api.test.ts`.
- Use `@testing-library/user-event` for interactions instead of `fireEvent`.
- Prefer testing hooks and pure helpers directly; keep component tests for
  behaviour a user can observe. `async` Server Components are out of scope
  for Vitest; use a browser check against the local stack for those.

### What is not covered

- No end-to-end browser tests. Pages, routing and the Mermaid / KaTeX
  renderers are verified manually against the local Docker stack.
- Real OpenAI and DeepSeek responses are never exercised in tests.

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
| `AI_REVIEW_ENABLED` | no | Grade each new AI answer into `ai_reviews` (default `false`; one extra DeepSeek call per generation) |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` | no | Enable Google Sign-In for students; all three must be set (see below) |
| `FRONTEND_URL` | no | Where the Google callback redirects the browser (default `http://localhost:3000`) |

Frontend (`frontend/.env.local`):

| Variable | Notes |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | Backend URL used by the browser, e.g. `http://localhost:8000` |
| `INTERNAL_API_URL` | Backend URL used by server-side rendering inside Docker, e.g. `http://backend:8000` |

### Google Sign-In setup

Students sign in with Google; admins keep email + password. The Google
button only appears when the backend reports it as configured
(`GET /api/v1/auth/providers`).

1. In the Google Cloud console create a project, configure the OAuth
   consent screen (external, scopes `openid` and `email` only, privacy
   policy URL required for publishing), and create an OAuth client of type
   "Web application".
2. Add the backend callback as an authorized redirect URI, e.g.
   `http://localhost:8000/api/v1/auth/google/callback` locally and the
   Render URL in production. It must match `GOOGLE_REDIRECT_URI` exactly.
3. Put the client ID and secret in `backend/.env` together with
   `GOOGLE_REDIRECT_URI` and `FRONTEND_URL`.

Students on under-18 Google Workspace for Education accounts may see
"Access blocked" until their school's admin allows the app; the login page
tells them to use a personal Google account instead.

### Prompts

All prompt texts are data: `backend/physics_ai_tutor/core/prompt_library.yaml`,
a list of records with `family`, `name`, `language` (`null` for texts shared
by both languages), `version`, `description`, and `text` (a YAML block scalar,
so the prose keeps real line breaks). The `prompts` module
and `concept_service` build their strings from it at import.

```bash
uv run python -m physics_ai_tutor.cli.show_prompts                 # read it
uv run python -m physics_ai_tutor.cli.show_prompts --family answer
```

To change wording: edit the YAML record, bump the family's `version`, run
the tests, and record the new fingerprint that `tests/test_prompts.py`
reports. Versions are stored on generated rows (`questions.prompt_version`,
`question_concepts.extraction_prompt_version`), which is what makes review
outcomes comparable across prompt changes.

### AI pre-review

With `AI_REVIEW_ENABLED=true`, every new AI answer is graded in the same
background task that translates it: a rubric prompt (family `ai_review` in
the prompt library, per-language) returns a JSON verdict stored in
`ai_reviews`. It is advisory only. Backfill the existing queue with:

```bash
uv run python -m physics_ai_tutor.cli.review_pending --limit 20
```

The command skips questions that already have a review and costs one
DeepSeek call per question, regardless of the flag.

### Exporting the review dataset

One JSONL line per human review, for offline analysis and prompt
evaluation. Rows before the 2026-10-28 data cutoff (no correction diff,
reason, or generation metadata) are skipped unless `--all`:

```bash
uv run python -m physics_ai_tutor.cli.export_reviews --out reviews.jsonl
uv run python -m physics_ai_tutor.cli.export_reviews --since 2026-11-01 --out nov.jsonl
uv run python -m physics_ai_tutor.cli.export_reviews --all > everything.jsonl
```

Admins can fetch the same file from `GET /api/v1/admin/reviews/export`
when the CLI has no database access. The line schema is documented in
[docs/database.md](database.md#review-dataset-export).

## Pull Request Checks

Before creating a pull request, run the same checks as CI:

```bash
# Backend (from backend/)
uv run pytest
uv run ruff check .
uv run mypy .

# Frontend (from frontend/)
npm run lint
npx tsc --noEmit
npm test
npm run build
```

## Further Reading

- [docs/database.md](database.md): schema, Alembic migrations, seed data
- [docs/api.md](api.md): endpoint reference and access rules
- [docs/security.md](security.md): security model and dependency policy

## Issues and Roadmap

Issues live in the repository itself via [git-bug](https://github.com/git-bug/git-bug)
(`brew install git-bug`). They are stored as git objects under `refs/bugs`,
separate from the file history, and are **not** pushed unless you run
`git bug push` explicitly. Work locally; do not push bug refs to the remote
unless that is intended.

The store sits in the repository's common `.git`, so **all worktrees share
the same bugs and identities**. Never run `git bug wipe`: it deletes every
bug and identity for every worktree. Use `git bug bug rm <id>` for a single
mistaken bug.

One-time setup on a new machine:

```bash
git bug user new --name "<name>" --email "<email>" --non-interactive
```

Everyday use:

```bash
git bug termui                 # browse, comment, label, close
git bug bug                    # list open issues
git bug bug -l P0              # by priority label
git bug bug -l M2              # by milestone label
git bug bug -l epic            # the roadmap issue
git bug bug show <id>          # one issue
```

Creating an issue: copy `docs/issues/TEMPLATE_task.md` (or
`TEMPLATE_bug.md`), fill it in, then

```bash
git bug bug new -t "<title>" -F <your-copy>.md
git bug bug label new <id> P1 M2 feature backend
```

Label conventions:

| Label | Meaning |
| --- | --- |
| `P0` … `P3` | P0 blocks deployment, P1 next, P2 planned, P3 later |
| `M0` … `M4` | Milestone: M0 Deploy Google Sign-In, M1 Student value, M2 Review data foundation, M3 AI-assisted review (advisory), M4 Partial automation and regression safety |
| `epic` | A tracking issue that links others (the roadmap) |
| topical | `backend`, `frontend`, `cli`, `prompt`, `review`, `ai-review`, `data-quality`, `observability`, `security`, `privacy`, `deploy`, `ops`, `testing`, `bug`, `feature` |

Cross-references inside an issue body are git-bug short ids (`#a1b2c3d`).

`docs/issues/NN-*.md` are the seed drafts (the roadmap is `00-roadmap.md`,
imported as the `epic`). `scripts/import_issues.py [dir] [--apply]` imports
them, skips titles that already exist, and rewrites `#NN` draft references
to real ids. After the import, git-bug is the source of truth; the drafts
are kept only so the tracker can be re-seeded in a fresh clone.
- [AGENTS.md](../AGENTS.md): project rules for contributors and coding agents
