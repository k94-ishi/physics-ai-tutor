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

### Several checkouts on one machine

Each git worktree can run its own stack. Copy
`docker-compose.override.yml.template` to `docker-compose.override.yml`
(gitignored), replace `NAME` with the worktree name and adjust the ports,
then prefix every compose command with `-p physics-ai-tutor-NAME`. Point
`frontend/.env.local` (`NEXT_PUBLIC_API_URL`) at the backend port you chose.

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
(a supplied English text is kept as a human translation). The file carries the
translations, tags and difficulty levels, and `seed_embeddings.jsonl.gz`
next to it carries their embeddings, so seeding calls neither OpenAI nor
DeepSeek (see
[docs/database.md](database.md#seed-data); write a local database back
into the files with `python -m physics_ai_tutor.cli.export_seed` and
`python -m physics_ai_tutor.cli.export_seed_embeddings`).
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
- The schema is built once per session with `alembic upgrade head`, so
  model/migration drift fails the suite (`tests/test_migrations.py`).
- Every test that uses `db` starts from empty tables: `reset_database()`
  deletes all rows and restarts the id sequences (ids start at 1, as
  `TRUNCATE ... RESTART IDENTITY` did, at ~2 ms instead of ~40 ms). It
  runs before each test only; the next test resets anyway.
- Passwords are hashed with Argon2 at minimal cost during tests (~0 ms
  instead of ~50 ms per hash); `tests/test_security.py` pins the
  production parameters, so the shortcut cannot leak into the app.
- Expensive read-only setup is shared with a module-scoped fixture, as
  `tests/test_seed.py` does for the full seed. Use it only when every test
  in the module just reads; anything that writes needs the per-test `db`.
- The whole backend suite takes about 40 s (2026-11-11, 522 tests; it was
  ~6 min before [66]). CI prints the 10 slowest tests.
- A PostgreSQL advisory lock is held for the session; a second concurrent
  run on the same database aborts immediately instead of corrupting it.

Layout of `backend/tests/`:

| File | Covers |
| --- | --- |
| `conftest.py` | Database lifecycle, `client` / `admin_client` / `user_client` fixtures, mocks for embeddings and concept extraction |
| `test_questions.py`, `test_users.py`, `test_auth.py`, `test_ai.py`, `test_health.py` | HTTP API, one file per router: status codes, auth rules, validation |
| `test_rate_limit.py` | Postgres-backed rate limiter: window counting, pruning, check/record split |
| `test_review_workflow.py` | End-to-end review flow: AI answer saved as unreviewed, hidden from students, approved / edited / rejected by an admin, history recorded |
| `test_*_service.py` | Service layer: RAG context, embeddings, concepts, recommendations, question lifecycle (`test_question_service.py` covers the five `question_*_service` modules) |
| `test_*_repository.py` | Repository queries against a real PostgreSQL + pgvector |
| `test_models.py` | Column defaults, cascades |
| `test_migrations.py` | Single Alembic head, models match migrations |
| `test_cli.py` | `create_user` and `translate_missing` CLIs, seed file checks |
| `test_seed.py` | One offline seed per module (OpenAI and DeepSeek forbidden), then read-only checks and export round trips |
| `test_security.py` | Production password hashing parameters (the test hasher is cheaper) |
| `test_comment_style.py` | Comments are English (Japanese only as quoted data) ([65]) |
| `test_architecture.py` | Layering rules: routers call services only; only the two `transaction()` helpers commit; sessions come from `database/`; async code never uses the sync helper ([69]) |
| `test_async_foundation.py` | Async engine, session, `async_transaction` commit/rollback, pool sizing ([69]) |
| `test_async_hot_path.py` | A pending generation does not hold the server; concurrent generations overlap ([70]) |
| `test_timing.py` | Stage timing logs and the request-path label ([68]) |
| `test_language_strict.py` | Students never get the other language on related/prerequisites/concepts; hidden rows are translated once in the background ([53]) |
| `test_language.py` | Bilingual rows: eager translation, provenance, `lang` resolution, English ask flow, cache tiers, review in either language, translate endpoint, import shapes |
| `test_concept_senses.py` | Concept senses ([55]): homonyms and synonyms at extraction, cross-language search and filter, admin editor (alias, label, merge, split), split CLI |
| `test_logging.py` | Request logging middleware |

Conventions:

- API tests use the `client` fixtures and assert on HTTP responses; service
  and repository tests take the `db` session directly.
- Anything that calls OpenAI or DeepSeek must be mocked. `conftest.py`
  already patches `embedding_service.create_embeddings`,
  `concept_service.extract_concept_names` and
  `translation_service.translate_qa` (which returns `"[en] <text>"` style
  markers so tests can assert on translations).
- Patch LLM seams through the `conftest` helpers, never with a bare
  `monkeypatch.setattr` ([70]): `patch_generation`,
  `patch_chat_completion`, `patch_create_embeddings` and
  `patch_rag_answer` each install one plain sync stub on *both* the sync
  and the `async_` function. Patching only one of them leaves the other
  pointing at the real API, which fails with an authentication error
  rather than an obvious one.
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
| `src/lib/__tests__/commentStyle.test.ts` | Comments are English (Japanese only as quoted data) ([65]) |
| `src/lib/api/__tests__/importBoundary.test.ts` | Nothing outside `lib/api` imports a feature file directly |
| `src/lib/__tests__/api.test.ts` | Request building (query params, JSON bodies, multipart), cookie inclusion, `ApiError` on non-2xx, 204 handling |
| `src/lib/__tests__/markdown.test.ts` | LaTeX delimiter normalisation for DeepSeek output |
| `src/lib/__tests__/concurrency.test.ts` | Concurrency limiter used by bulk admin actions |
| `src/lib/hooks/__tests__/useQueryState.test.tsx` | URL-backed list state (defaults omitted, `router.replace` without scroll) |
| `src/lib/i18n/__tests__/` | Translation tables have identical keys and placeholders in `ja` and `en`; language switching, persistence, `<html lang>` |
| `src/lib/auth/__tests__/AuthContext.test.tsx` | Session bootstrap, 401 treated as logged out, login / logout state |
| `src/components/ui/__tests__/` | `Pagination`, `StatusMessage`, `ConfirmDialog`: rendering, accessibility roles, callbacks, keyboard handling |
| `src/components/admin/__tests__/AdminQuestionCard.test.tsx` | Admin queue card: each action calls only its callback; selection toggling |
| `src/lib/hooks/__tests__/useLatestRequest.test.tsx` | Only the newest request stays current; cancel; stable object |

Conventions:

- Wrap components in `LanguageProvider` and query by role and visible text
  (Japanese, the default language) rather than by CSS class.
- Mock `@/lib/api` with `vi.mock` for components that load data; mock
  `fetch` only in `api.test.ts`.
- Use `@testing-library/user-event` for interactions instead of `fireEvent`.
- Prefer testing hooks and pure helpers directly; keep component tests for
  behaviour a user can observe. `async` Server Components are out of scope
  for Vitest; use a browser check against the local stack for those.

### Backend layers and transactions

AGENTS.md asks for router -> service -> repository. Since [59] this is
enforced by `tests/test_architecture.py`:

- **Routers** (`api/`) parse input, authorise, call one service and map
  domain errors to HTTP. They never import `repositories`, open a session,
  or call `db.query/get/add/commit/...`.
- **Services** own the use case and its transaction. Wrap the writes of a
  use case in `with transaction(db, "operation"):`
  (`database/transaction.py`): it commits on success, and on any error
  rolls back, logs `Rolling back transaction: operation=...` and re-raises.
  For best-effort work, put the `with` inside your own `try/except`. It is
  the only code that calls `commit()` or `rollback()`.
- **Repositories** query and flush; they never commit.
- **Question use cases** live in five modules (since [60]):
  `question_read_service` (list, detail, exact match, ask cache),
  `question_write_service` (create, import, update, delete, AI answers,
  concept extraction), `question_review_service` (approve / edit-approve /
  reject, history), `question_translation_service` (machine translation and
  per-language embeddings) and `question_presentation_service` (response
  shaping). Routers: `api/v1/questions.py` (public reads) and
  `api/v1/admin_questions.py` (admin writes), same `/questions` prefix.
- **Response language** (since [62]): a router builds one
  `ResponseLanguage.for_caller(lang, admin=...)` per request. Students are
  `strict` (never the other language, [53]); admins get the fallback.
  Services take it as `language=` (a plain `Language` means the fallback)
  and return what a strict response left out as `TranslationNeeds`; the
  router hands those to the background translator in one call. List
  filters travel as one `QuestionFilters` object from router to repository.
- **Background tasks** open their session with `background_session()`
  (`database/session.py`); tests point that one helper at the test
  database. CLIs keep their own `SessionLocal`.

### Two stacks during the async migration ([69])

Track F ([67]) converts the backend to async one vertical slice at a
time, so a sync and an async stack coexist until [73] retires the sync
one from the app. Both use the same psycopg driver and the same
`DATABASE_URL`; only the calling style differs.

| | Sync (not yet converted) | Async (converted) |
| --- | --- | --- |
| Request session | `Depends(get_db)` | `Depends(get_async_db)` |
| Background session | `with background_session()` | `async with async_background_session()` |
| Writes | `with transaction(db, "op")` | `async with async_transaction(db, "op")` |
| Test fixture | `db` | `async_db` |
| Engine | `engine` / `SessionLocal` | `async_engine` / `AsyncSessionLocal` |

Rules, all enforced by `tests/test_architecture.py`:

- **A slice is converted whole or not at all.** Router, services and
  repositories of one call chain move together. Never call a sync
  repository from an async service, and never bridge with
  `run_in_executor` — convert the callee instead.
- **Shared functions get an `async_` twin, not a rewrite.** A repository
  or service used by both converted and unconverted callers keeps its
  sync function and gains `async_<name>` beside it ([70]); [73] deletes
  the sync half and drops the prefix. Where the two would otherwise
  duplicate a rule, extract it: the status predicate
  (`_status_conditions`), the vector-search statement
  (`_similar_embeddings_select`) and the strict-language naming
  (`_names_by_question`) are shared by both variants on purpose, because
  a filter drifting between them is a security bug, not a style problem.
- **Read what you need off an ORM row before a transaction that might
  roll back.** A rollback expires the object, and reading an expired
  attribute afterwards is implicit IO, which `AsyncSession` refuses with
  `MissingGreenlet` — so an error path that logs `question.id` crashes
  instead of logging. `async_review_question` captures its scalars up
  front for exactly this reason.
- Only `database/` (and script entry points: `cli/`, `database/seed.py`)
  may build a session factory. Everything else takes a session.
- `async_transaction` is the only way async code commits. A plain
  `with transaction(...)` inside an `async def` is a silent bug — it
  would call `commit()` without awaiting, so the block looks fine and
  writes nothing. There is a test that fails on exactly that shape.
- Async tests are marked `pytest.mark.anyio` (module-level
  `pytestmark`); the `anyio_backend` fixture pins asyncio. The anyio
  plugin ships with anyio, so there is no new test dependency.
- `AsyncSession` raises on implicit IO, so a relationship the sync code
  loaded lazily needs `selectinload` or an explicit query once its slice
  is converted.

Both session factories keep `expire_on_commit=False`: services return ORM
objects whose attributes are read after the commit, and an async refresh
would need an await the caller cannot give.

Pool sizes are explicit (`POOL_SIZE`, `MAX_OVERFLOW` in
`database/database.py`) because during the migration two pools add up
against one connection limit; [74] tunes the final numbers for the
Supabase pooler, and [75] settles how they multiply across workers.

### URL parameters on the student list

Four parameters shape the student list and compose with pagination:
`?keyword=` (lexical, written debounced), `?concept=` (chip navigation,
[41]), `?similar=` (vector search, [49]), and `?lang=ja|en` ([50]).
`lang` makes a shared link mean the same thing for every recipient - the
vector search is language-scoped, so without it a `?similar=` link
searches the recipient's stored language and can quietly return nothing.
URL wins over the stored preference but never overwrites it; the header
switcher updates `lang` only when the URL already carries it, and a
language switch keeps a `similar=` query and re-runs it against the new
language's embeddings (owner's decision, 2026-11-02). Language-dependent
effects must wait for `useLanguage().resolved`, or they run once under
the default `ja` and again under the resolved language. `similar` is
written only on submit - unlike a keyword it costs an embedding call to
restore - and the restore path skips the exact-match redirect so the back
button never bounces forward. Query embeddings are cached server-side in
`query_embeddings`, keyed by (normalised-text hash, embedding model); a
model upgrade misses the cache by construction instead of mixing
incompatible vectors.

### Frontend building blocks ([63])

- `useLatestRequest()` (`lib/hooks`): `const isCurrent = req.begin()` before
  a fetch, `if (!isCurrent()) return` after it; `req.cancel()` makes older
  requests stale. Use it instead of a hand-written request counter.
- `QuestionCard` (`components/ui`): question, answer preview and tags,
  opening the preview; `tone="emerald"` for "Read these first".
- The API client is `lib/api/` ([64]): `client.ts` (base URLs,
  `apiFetch`, `ApiError`) and one file per feature (`questions`, `concepts`,
  `auth`, `users`, `admin`, `ai`). Always import from `@/lib/api`: tests
  mock that module, and `lib/api/__tests__/importBoundary.test.ts` fails on
  a direct feature import.
- Translations are `lib/i18n/translations/` ([64]): one file per feature
  (`common`, `student`, `account`, `admin`, `adminStats`, `levels`,
  `conceptsAdmin`), each with `ja` and an `en` typed against it; add a key
  to the file of its feature. Import from `@/lib/i18n/translations`.
- The admin queue (`app/admin/questions/`) is a page plus two hooks:
  `useAdminQueueList` (URL filters, loading, searches, paging) and
  `useAdminQueueActions` (selection, review, bulk, extraction, AI review,
  delete), and two components, `AdminQueueFilters` and `AdminQuestionCard`.

### Naming: "tag" on screen, "concept" in code

Students and teachers see **タグ / tag** (owner, 2026-11-10); the code,
tables and API keep the developer name `concept` (`concepts`,
`concept_terms`, `?concept=`, `ConceptChips`). Translation keys keep their
`concepts.*` prefix. Keep physics wording that is not about the tag
feature (「抽象概念」 in the level rubric, the `UNNEEDED_TOOLS` reason
text) as it is. Tag chips carry no visible heading; the list has the
accessible name "タグ"/"Tags".

### The sticky ask bar

`StickyAskBar` ([43]) fixes the ask box to the bottom of the question
detail page. It measures itself and publishes `--ask-bar-height`; any
other bottom-fixed element must offset by that variable (`Toaster`
already does) or it will sit underneath the bar. The root layout sets
`interactiveWidget: "resizes-content"` so a soft keyboard resizes the
page rather than covering the bar.

### Markdown rendering

`MarkdownContent` composes remark-gfm, remark-math, rehype-katex and
**remark-cjk-friendly**. The last one is not optional: CommonMark counts
fullwidth punctuation (`」）。、`) as punctuation, so a `**` between `」`
and a kana can only *open* emphasis, never close it, and
`**「重心の位置」**と...` renders with literal asterisks. Japanese has no
spaces to rescue the delimiter classification. The plugin implements the
CJK-friendly flanking amendment and fixes it at render time, so stored
answers never need editing for it (issue [36]). Keep it in the plugin
list, and cover any new renderer with
`src/components/ui/__tests__/MarkdownContent.test.tsx`.

### Host builds and the dev container

The compose frontend mounts `./frontend`, including `.next`. Running
`npm run build` on the host while that container runs overwrites its
Turbopack cache and the dev server exits ("Failed to open database").
Restart it with `docker compose -p <project> up -d frontend`.

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

### Nightly AI review (`.github/workflows/ai-review-nightly.yml`)

Runs `review_pending --scope both --trigger scheduled` every day at
17:00 UTC (02:00 JST). The runner is GitHub Actions rather than a Render
cron job or an in-process scheduler ([26]): no new infrastructure, the
logs live next to the repo, and the Supabase *pooler* URL is reachable
from Actions. The trade-off is that the production `DATABASE_URL` lives
in a GitHub secret.

Pricing assumptions (checked 2026-10-30; DeepSeek changes them, re-check
before relying on the numbers): no Batch API (`/batches` returns 404),
but requests in UTC 16:30-00:30 are discounted, and the long shared
rubric prefix is cheap on repeated calls thanks to context caching - a
dense nightly run maximises both. The window lives in
`AI_REVIEW_OFFPEAK_START/END`; the CLI refuses to start outside it
without `--force`, so a mis-set cron fails loudly (exit 2) instead of
paying full price. A failed run exits 1 and fails the job, which triggers
GitHub's failure e-mail; results are also on `/admin/stats`.

Required repository secrets: `DATABASE_URL` (Supabase pooler) and
`DEEPSEEK_API_KEY`. With the nightly in place, `AI_REVIEW_ENABLED` can
stay `false` in production: teachers find fresh verdicts in the morning
and generation never pays for an inline review call.

## Reading latency logs ([68])

Every request logs its total time
(`Response: POST /api/v1/ai/ask 200 20913.08ms`), and the waiting parts
inside it log their own:

```
Stage finished: name=ask_cache_lookup path=/api/v1/ai/ask duration_ms=6.33 hit=False
Stage finished: name=embed_query     path=/api/v1/ai/ask duration_ms=336.78 cache=miss
Stage finished: name=vector_search   path=/api/v1/ai/ask duration_ms=40.01 limit=5 results=5
Stage finished: name=deepseek_chat   path=/api/v1/ai/ask duration_ms=20033.74 completion_tokens=200
Stage finished: name=save_answer     path=/api/v1/ai/ask duration_ms=420.22
```

The top-level stages of one request add up to its total, so a slow
request can be explained without guessing. Points to know:

- Stages nest. `rag_context` contains `embed_query` (which contains
  `openai_embeddings`) and `vector_search`; do not add a stage to its own
  parent when summing.
- `path=background:...` means work that ran *after* a response was sent
  (translation, AI review). It is not charged to any request.
- A failed call still logs its duration, because waiting for a timeout is
  latency too.
- Wrap a new slow step with `timing.stage("name")` from
  `core/timing.py`, in a service (never a router). `stage.note(...)`
  adds fields such as `cache=hit`.

To measure rather than read, use the two dev scripts:

```bash
# Concurrency and percentiles against a LOCAL stack (refuses other hosts).
python scripts/latency_probe.py --path /api/v1/health -n 40 -c 1
python scripts/latency_probe.py --path /api/v1/ai/ask \
  --body '{"question":"テスト {n}"}' -n 60 -c 60    # {n} keeps each request distinct

# A stand-in for OpenAI/DeepSeek with a known delay, so generation time is
# a constant instead of a variable. No API key, no quota.
python scripts/fake_llm_server.py --port 9100 --chat-delay 20
# then run the backend with OPENAI_BASE_URL and DEEPSEEK_BASE_URL set to it
```

The probe's own thread pool is sized to `-c`; asyncio's default executor
caps near 12 threads and would otherwise silently become the limit.
Baseline numbers and how they were taken are in
[docs/issues/68-latency-baseline-and-stage-timing.md](issues/68-latency-baseline-and-stage-timing.md).

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
| `AI_REVIEW_DAILY_CAP` | no | Rolling 24h budget of reviewer calls across all runs (default `200`) |
| `AI_REVIEW_MAX_TOKENS` | no | Output budget for reviewer calls (default `3000`); below ~2500 the JSON with a full suggested answer gets truncated |
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
uv run python -m physics_ai_tutor.cli.review_pending --limit 20            # no review yet
uv run python -m physics_ai_tutor.cli.review_pending --scope stale         # older rubric version
```

Every invocation is recorded as a run (`ai_review_runs`): scope, counts,
token totals, status. Only one run may execute at a time, and all runs
share a rolling 24h budget (`AI_REVIEW_DAILY_CAP`, default 200 calls).
Admins can start and watch runs from the API (`/admin/ai-review/runs`);
each question costs one DeepSeek call regardless of `AI_REVIEW_ENABLED`.

### Measuring AI-reviewer agreement

Each human review on a question that already had an AI verdict forms a
pair (the latest `ai_reviews` row created *before* the human review; the
backlog case where a teacher reviewed first is excluded). The admin stats
page shows the agreement section; the same tables print from:

```bash
uv run python -m physics_ai_tutor.cli.review_metrics            # since the data cutoff
uv run python -m physics_ai_tutor.cli.review_metrics --all
uv run python -m physics_ai_tutor.cli.review_metrics --from-file reviews.jsonl   # offline, from an export
```

The export carries each review's paired AI verdict (`ai_*` fields), so
`--from-file` on an `export_reviews` snapshot gives the same numbers as the
database path - handy for sharing a reproducible snapshot or analysing a
production export on a laptop.

Read it like this: **exact agreement** is AI `APPROVE`/`EDIT`/`REJECT`
matching teacher `APPROVE`/`EDIT_APPROVE`/`REJECT` one-to-one;
**publish agreement** collapses that to publish-vs-withhold. **Reject
precision** is how often an AI reject was confirmed by the teacher (the
number that decides whether auto-reject is safe); **reject recall** is how
many teacher rejects the AI caught. The **calibration table** shows
agreement per confidence decile - a policy should only act in buckets with
enough pairs and very high agreement. Unparsed AI output counts as
disagreement everywhere. Under 30 pairs every block is marked too small.

### DeepSeek pricing notes (checked 2026-10-30)

DeepSeek offers no Batch API: `GET /batches` on the live endpoint returns
404 (`/models` and `/files` exist). Cheaper reviewing therefore means
running the backlog in the off-peak discount window (UTC 16:30-00:30, JST
01:30-09:30) and relying on context caching of the long rubric prefix;
see the AI review run issues ([25]-[28]) for the scheduler and admin
triggers. Re-check DeepSeek's pricing page before relying on the window.

### Prompt regression check (golden set)

`backend/eval/golden.jsonl` is a hand-labelled set of Q&A pairs (see
`backend/eval/README.md`; the starter set is labelled by construction and
should grow to 50-100 teacher-verified cases). The check grades every case
with the current reviewer prompt at temperature 0 and compares the
agreement metrics against the committed baseline for the same prompt
versions:

```bash
uv run python -m physics_ai_tutor.cli.eval_prompts --dry-run        # validate only, no API
uv run python -m physics_ai_tutor.cli.eval_prompts                  # grade + compare (12+ DeepSeek calls)
uv run python -m physics_ai_tutor.cli.eval_prompts --regenerate     # also regenerate answers (2x calls)
uv run python -m physics_ai_tutor.cli.eval_prompts --save-baseline  # pin the current numbers
```

Exit code 1 means a metric dropped more than the tolerance (default 0.05)
below the baseline - the prompt change regressed. Add `--verbose` to print
the reviewer's rationale on every disagreement; that is what a teacher
needs to decide whether the label or the model is right. Runs are not
bit-reproducible (about 3 of 69 verdicts flip between identical runs), so
re-run once before trusting a change near the tolerance. The "Prompt Eval" GitHub
Actions workflow (`workflow_dispatch`) runs the same thing with the
repository's `DEEPSEEK_API_KEY`; no database is needed. Run it before
merging changes to the `answer` or `ai_review` prompt families (rule in
`AGENTS.md`).

### Splitting concepts merged by the old rule ([55])

Before [55] an extracted pair joined any concept sharing one of its words,
and the other word was dropped (相 | phase landed on 位相 | phase). The
stored data no longer says which word was dropped, so detection is a
heuristic: a link is a candidate when the question's own text uses none of
the sense's words in its original language. That also catches many
correct links whose concept the text only implies (236 links on 105 of the
144 seed questions), which is safe: re-extraction only replaces that
question's links, under the new matching.

```bash
uv run python -m physics_ai_tutor.cli.split_merged_concepts --dry-run   # report, offline
uv run python -m physics_ai_tutor.cli.split_merged_concepts --limit 50  # re-extract (DeepSeek)
```

On production the `backfill_levels` pass ([54]) re-extracts every APPROVED
question anyway, which applies the same split. Remaining mistakes are fixed
by hand in `/admin/manage/concepts` (merge / split / alias).

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
- [AGENTS.md](../AGENTS.md): project rules for contributors and coding agents
- [docs/issues/](issues/): the issue tracker; `status.md` is the index and
  the only place a status lives, each `NN-slug.md` carries the body. The
  git-bug store is a read-only archive of everything before 2026-11-02.
