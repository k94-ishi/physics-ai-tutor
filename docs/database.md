# Database Guide

This document describes the PostgreSQL schema of Physics AI Tutor, how the
schema is versioned with Alembic, and how to work with the database during
development.

The schema is the single source of truth for the RAG knowledge base:
every question, its vector embeddings, extracted physics concepts, and the
review history of AI-generated content live here. It also acts as the
answer cache for the ask-AI flow (see [Cache and knowledge base](#cache-and-knowledge-base)).

Each question row carries its text in **both supported languages**
(Japanese and English). Review status applies to the physics content and
therefore to every language of a row; translations are machine-generated
when a row is created and labelled by provenance.

---

## Overview

- Engine: PostgreSQL 17 with the [pgvector](https://github.com/pgvector/pgvector) extension
- ORM: SQLAlchemy 2.x (declarative, `Mapped[]` style)
- Migrations: Alembic (`backend/alembic/`)
- Driver: `psycopg` v3 (`postgresql+psycopg://...`)
- Local database: `pgvector/pgvector:pg17` via Docker Compose
- Production database: Supabase PostgreSQL (pgvector enabled)

All ORM models are defined in `backend/physics_ai_tutor/models/` and share a
single `Base` from `backend/physics_ai_tutor/database/base.py`. Alembic
autogenerate compares that metadata to the live database.

---

## Entity Relationship Diagram

```mermaid
erDiagram
    questions ||--o{ question_embeddings : "has"
    questions ||--o{ question_concepts : "tagged with"
    concepts  ||--o{ question_concepts : "tags"
    questions ||--o{ question_reviews : "reviewed in"
    users     ||--o{ question_reviews : "performs"

    questions {
        int id PK
        text question_ja "nullable"
        text answer_ja "nullable"
        varchar(10) ja_provenance "ORIGINAL | HUMAN | MACHINE"
        text question_en "nullable"
        text answer_en "nullable"
        varchar(10) en_provenance "ORIGINAL | HUMAN | MACHINE"
        varchar(10) original_language "ja | en"
        varchar(20) status "UNREVIEWED | APPROVED | REJECTED"
        varchar(20) source "MANUAL | AI_GENERATED | RAG_RESULT"
        int[] retrieved_question_ids
        timestamptz created_at
        timestamptz updated_at
    }

    question_embeddings {
        int id PK
        int question_id FK
        varchar(10) language "ja | en"
        varchar(50) type "question | answer"
        int chunk_index "nullable"
        vector(1536) embedding
        varchar model
        timestamptz created_at
        timestamptz updated_at
    }

    concepts {
        int id PK
        varchar(255) name_ja UK "nullable"
        varchar(255) name_en UK "nullable"
        vector(1536) embedding
        varchar extraction_model
        varchar embedding_model
        varchar extraction_prompt_version
        timestamptz created_at
        timestamptz updated_at
    }

    question_concepts {
        int question_id PK, FK
        int concept_id PK, FK
    }

    question_reviews {
        int id PK
        int question_id FK
        varchar(20) action "APPROVE | EDIT_APPROVE | REJECT"
        varchar(10) language "text the reviewer edited"
        text before_question
        text before_answer
        text after_question
        text after_answer
        int reviewer_id FK "nullable"
        text comment
        timestamptz created_at
    }

    users {
        int id PK
        varchar email UK
        varchar hashed_password
        varchar role "admin | user"
        timestamp created_at
    }
```

---

## Tables

### `questions`

The core knowledge table. One row is a single physics question/answer unit
with its text in each language.

| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| `id` | `integer` | no | serial | Primary key |
| `question_ja`, `answer_ja` | `text` | yes | | Japanese text. Both present or both `NULL` (check constraint). |
| `ja_provenance` | `varchar(10)` | yes | | How the Japanese text came to be: `ORIGINAL`, `HUMAN`, `MACHINE`. `NULL` when there is no Japanese text. |
| `question_en`, `answer_en` | `text` | yes | | English text, same rules. |
| `en_provenance` | `varchar(10)` | yes | | As above for English. |
| `original_language` | `varchar(10)` | no | `'ja'` | Language the question was asked or written in. That text is the ground truth; the other language is derived from it. |
| `status` | `varchar(20)` | no | `'APPROVED'` | Review state of the physics content. Indexed. Applies to every language. |
| `source` | `varchar(20)` | no | `'MANUAL'` | How the row was produced. |
| `retrieved_question_ids` | `integer[]` | no | `'{}'` | IDs of approved questions used as RAG context. Language independent. |
| `generation_model` | `varchar` | yes | | LLM that generated the answer; `NULL` for manual/imported rows. |
| `prompt_version` | `varchar(20)` | yes | | `prompts.ANSWER_PROMPT_VERSION` at generation time. |
| `generation_mode` | `varchar(10)` | yes | | `DIRECT` or `RAG`. |
| `prompt_tokens` | `integer` | yes | | Usage reported by the API. |
| `completion_tokens` | `integer` | yes | | Usage reported by the API. |
| `created_at`, `updated_at` | `timestamptz` | no | `now()` | `updated_at` refreshed by the ORM. |

Constraints: `questions_has_text` (at least one language present),
`questions_ja_pair` and `questions_en_pair` (question and answer of a
language are both set or both `NULL`). Duplicate detection is application
side, per language column.

`status`, `source` and provenance are plain strings; valid values live in
`backend/physics_ai_tutor/schemas/question.py` and `schemas/language.py`:

| `status` | Meaning |
| --- | --- |
| `UNREVIEWED` | Generated by AI and not yet checked by an admin. Hidden from non-admin users on browse paths, but reused as a **cache hit** by the ask flow (see below). |
| `APPROVED` | Verified content. Visible to users, eligible as RAG context, triggers concept extraction. |
| `REJECTED` | Reviewed and declined. Hidden from non-admin users, never served from cache, excluded from retrieval. |

| `source` | Meaning |
| --- | --- |
| `MANUAL` | Created by an admin (form, JSONL import, or seed). |
| `AI_GENERATED` | Produced by a direct LLM call with no retrieved context. |
| `RAG_RESULT` | Produced by the RAG pipeline; `retrieved_question_ids` records the context used. |

| provenance | Meaning |
| --- | --- |
| `ORIGINAL` | The text as asked, written, or generated. Always the `original_language` side. |
| `HUMAN` | Translation written by a person (admin form, import with both languages, seed). Never overwritten automatically. |
| `MACHINE` | Translation produced by the Translator (DeepSeek). Regenerated automatically when the other side is edited by a human. |

Lifecycle:

1. A row is created with text in its original language. If the other
   language is not supplied, it is machine translated immediately (for AI
   answers, in a background task right after the student gets the reply)
   and embedded, so reviewers can read either language.
2. Answers from `POST /api/v1/ai/ask` start as `UNREVIEWED`.
3. An admin review moves the row to `APPROVED` or `REJECTED` and appends a
   `question_reviews` row recording which language was reviewed or edited.
   `EDIT_APPROVE` in one language regenerates a `MACHINE` counterpart.
4. On `APPROVED`, physics concepts are extracted (one call returns both
   language names) and any still-missing language is translated.
5. Rows approved before this schema existed are filled lazily on their
   first public view in the missing language, or in bulk with the
   `translate_missing` CLI.

### `question_embeddings`

Vector embeddings for semantic search. Each question normally has two rows:
one for the question text and one for the answer text.

| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| `id` | `integer` | no | serial | Primary key |
| `question_id` | `integer` | no | | FK to `questions.id`, `ON DELETE CASCADE` |
| `language` | `varchar(10)` | no | `'ja'` | Language of the embedded text. Indexed. A row has one `question` and one `answer` vector per language it has text for. |
| `type` | `varchar(50)` | no | | `question` or `answer`. Similarity search uses `question`. |
| `chunk_index` | `integer` | yes | `NULL` | Reserved for chunked long answers. Currently always `NULL`. |
| `embedding` | `vector(1536)` | no | | OpenAI `text-embedding-3-small` output. |
| `model` | `varchar` | no | | Embedding model name, recorded for future re-embedding. |
| `created_at` | `timestamptz` | no | `now()` | |
| `updated_at` | `timestamptz` | no | `now()` | |

Similarity search orders by cosine distance (`<=>` operator) within one
language and joins back to `questions` to filter by status. Cross-language
scoring is not used: because every row is embedded in each language it has
text for, a same-language search already finds rows that originated in the
other language. There is currently no vector index
(HNSW or IVFFlat); searches are sequential scans, which is fine at the
current data size. Add an index via a migration if the table grows large.

Embeddings for a language are regenerated whenever that language's text
changes (create, translate, update, edit-approve). Deleting a question
removes its embeddings by cascade.

### `concepts`

Physics concepts extracted from approved questions by the LLM. Used for
concept-based "related questions" recommendations.

| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| `id` | `integer` | no | serial | Primary key |
| `name_ja` | `varchar(255)` | yes | | Japanese name, unique. |
| `name_en` | `varchar(255)` | yes | | English name, unique. At least one name is set; a missing side is filled when a later extraction supplies it. |
| `embedding` | `vector(1536)` | no | | Embedding of the concept name. |
| `extraction_model` | `varchar` | no | | LLM used to extract the concept (e.g. `deepseek-chat`). |
| `embedding_model` | `varchar` | no | | Embedding model used for `embedding`. |
| `extraction_prompt_version` | `varchar` | no | | Prompt version string (`CONCEPT_EXTRACTION_PROMPT_VERSION`, currently `v2`, which returns `<ja> | <en>` pairs). |
| `created_at` | `timestamptz` | no | `now()` | |
| `updated_at` | `timestamptz` | no | `now()` | |

The three provenance columns exist so concepts can be selectively
re-extracted when the model or prompt changes.

### `question_concepts`

Many-to-many join between `questions` and `concepts`.

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `question_id` | `integer` | no | PK part, FK to `questions.id`, `ON DELETE CASCADE` |
| `concept_id` | `integer` | no | PK part, FK to `concepts.id`, `ON DELETE CASCADE` |

### `question_reviews`

Append-only audit log of admin review actions on a question.

| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| `id` | `integer` | no | serial | Primary key |
| `question_id` | `integer` | no | | FK to `questions.id`, `ON DELETE CASCADE` |
| `action` | `varchar(20)` | no | | `APPROVE`, `EDIT_APPROVE`, or `REJECT` |
| `reason` | `varchar(30)` | yes | | Why the answer was rejected or edited (`PHYSICS_ERROR`, `OFF_TOPIC`, ...); `NULL` for plain approvals and for all rows created before 2026-10-28. |
| `language` | `varchar(10)` | no | `'ja'` | Language the reviewer read or edited; the before/after snapshots are in this language. |
| `before_question` | `text` | yes | | Snapshot before the action |
| `before_answer` | `text` | yes | | Snapshot before the action |
| `after_question` | `text` | yes | | Snapshot after the action (set for `EDIT_APPROVE`) |
| `after_answer` | `text` | yes | | Snapshot after the action (set for `EDIT_APPROVE`) |
| `reviewer_id` | `integer` | yes | | FK to `users.id`, `ON DELETE SET NULL`. Becomes `NULL` when the reviewer account is deleted so the audit trail survives. |
| `comment` | `text` | yes | | Optional reviewer note |
| `created_at` | `timestamptz` | no | `now()` | |

Rows are never updated. Query them with `GET /api/v1/questions/{id}/reviews`
(admin only).

### `users`

Admin accounts (password) and student accounts (Google Sign-In).

| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| `id` | `integer` | no | serial | Primary key |
| `email` | `varchar` | no | | Unique, indexed (`ix_users_email`). |
| `hashed_password` | `varchar` | yes | | Argon2 hash via `pwdlib`; `NULL` for Google accounts. |
| `auth_provider` | `varchar` | no | `'password'` | `password` or `google`. |
| `google_sub` | `varchar` | yes | | Google's stable subject id; unique (`ix_users_google_sub`), `NULL` for password accounts. |
| `role` | `varchar` | no | `'user'` (ORM default) | `admin` or `user`. Default is applied by SQLAlchemy, not the database. |
| `created_at` | `timestamp` | no | `now()` | Note: timezone-naive, unlike other tables. |

Two check constraints tie the provider to its credential:
`users_password_provider` (`auth_provider = 'password'` iff
`hashed_password IS NOT NULL`) and `users_google_provider`
(`auth_provider = 'google'` iff `google_sub IS NOT NULL`).

Students self-register through Google Sign-In and always get role `user`.
Create the first admin with the CLI (see
[Creating an admin user](#creating-an-admin-user)); further password
accounts can be created by an admin through `POST /api/v1/users`.

### `question_asks`

One row per signed-in ask, cache hit or fresh generation; anonymous asks are
not recorded. Powers `GET /users/me/questions` and the planned usage counts.

| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| `id` | `integer` | no | serial | Primary key |
| `question_id` | `integer` | no | | FK → `questions.id`, `ON DELETE CASCADE`, indexed. |
| `user_id` | `integer` | yes | | FK → `users.id`, `ON DELETE SET NULL`: deleting the account unlinks the history but keeps aggregate counts. |
| `cache_hit` | `boolean` | no | `false` | True when the answer came from the cache; set explicitly by the recorder, not inferred from timestamps. |
| `language` | `varchar(10)` | no | `'ja'` | Language the student asked in. |
| `created_at` | `timestamptz` | no | `now()` | |

Index `ix_question_asks_user_created` on (`user_id`, `created_at`) serves the
per-user listing.

Note on review history data: rows created before 2026-10-28 by the admin
UI's "Save and approve" have `action = 'APPROVE'` with `before_* = after_*`
even when the teacher edited the text first (the edit went through a
separate `PUT`). Analyses of corrections should exclude rows from before
that date.

### `ai_reviews`

Verdicts from the AI pre-reviewer ([13] fills it), kept apart from the human
history so agreement between the two can be measured ([15]). Advisory only;
rows here never change a question's status.

| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| `id` | `integer` | no | serial | Primary key |
| `question_id` | `integer` | no | | FK → `questions.id`, `ON DELETE CASCADE`. |
| `language` | `varchar(10)` | no | `'ja'` | Language of the graded text. |
| `verdict` | `varchar(10)` | yes | | `APPROVE`, `EDIT`, or `REJECT`; `NULL` when the model output could not be parsed (raw text kept in `rationale`). |
| `confidence` | `float` | yes | | 0–1. |
| `reasons` | `varchar[]` | no | `{}` | Codes from the human review vocabulary (`question_reviews.reason`). |
| `rationale` | `text` | yes | | Free-text justification. |
| `suggested_answer` | `text` | yes | | Proposed correction, if any. |
| `rubric` | `jsonb` | yes | | Per-criterion scores; JSONB so criteria can evolve without migrations. |
| `model`, `prompt_version` | `varchar` | no | | Which reviewer produced the verdict. |
| `prompt_tokens`, `completion_tokens` | `integer` | yes | | Usage. |
| `created_at` | `timestamptz` | no | `now()` | Indexed with `question_id` (`ix_ai_reviews_question_created`). |

`question_reviews` additionally gained `reviewer_kind` (`human` default,
`ai`, `policy`) and a nullable `policy_name`, so when a policy is later
allowed to act, its status changes are ordinary review rows that remain
distinguishable from a teacher's.

### `ai_review_runs`

One row per AI reviewer invocation (scheduled, manual, or CLI): scope,
the fixed list of question ids chosen at start, requested/reviewed/failed
counts (updated per question so progress can be polled), token totals,
status (`running`/`done`/`failed`/`cancelled`), timestamps, and the admin
who started it (`SET NULL` on account deletion). A partial unique index
(`uq_ai_review_runs_single_running`) allows at most one `running` row;
runs stuck beyond 30 minutes are marked failed by the next start.

### `rate_limit_hits`

One row per counted request for the sliding-window rate limiter (see
[docs/security.md](security.md#abuse-and-cost-control)).

| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| `id` | `integer` | no | serial | Primary key |
| `action` | `varchar` | no | | `ai_ask` or `login`. |
| `bucket_key` | `varchar` | no | | `ip:<address>` for anonymous callers, `user:<id>` for signed-in callers. |
| `created_at` | `timestamp` | no | `now()` | Compared against the database clock. |

Rows older than one day are pruned opportunistically on about 1% of
record calls, so the table stays small without a scheduled job.

---

## Indexes and Constraints

| Name | Table | Definition |
| --- | --- | --- |
| `questions_pkey` | `questions` | PK (`id`) |
| `ix_questions_status` | `questions` | btree (`status`) |
| `question_embeddings_pkey` | `question_embeddings` | PK (`id`) |
| `concepts_pkey` | `concepts` | PK (`id`) |
| `concepts_name_ja_key` | `concepts` | UNIQUE (`name_ja`) |
| `concepts_name_en_key` | `concepts` | UNIQUE (`name_en`) |
| `ix_question_embeddings_language` | `question_embeddings` | btree (`language`) |
| `question_concepts_pkey` | `question_concepts` | PK (`question_id`, `concept_id`) |
| `question_reviews_pkey` | `question_reviews` | PK (`id`) |
| `users_pkey` | `users` | PK (`id`) |
| `ix_users_email` | `users` | UNIQUE btree (`email`) |
| `ix_users_google_sub` | `users` | UNIQUE btree (`google_sub`) |
| `users_password_provider` | `users` | CHECK provider/password pairing |
| `question_asks_pkey` | `question_asks` | PK (`id`) |
| `ix_question_asks_question_id` | `question_asks` | btree (`question_id`) |
| `ix_question_asks_user_created` | `question_asks` | btree (`user_id`, `created_at`) |
| `users_google_provider` | `users` | CHECK provider/google_sub pairing |
| `rate_limit_hits_pkey` | `rate_limit_hits` | PK (`id`) |
| `ix_rate_limit_hits_window` | `rate_limit_hits` | btree (`action`, `bucket_key`, `created_at`) |

Foreign keys:

| From | To | On delete |
| --- | --- | --- |
| `question_embeddings.question_id` | `questions.id` | CASCADE |
| `question_concepts.question_id` | `questions.id` | CASCADE |
| `question_concepts.concept_id` | `concepts.id` | CASCADE |
| `question_reviews.question_id` | `questions.id` | CASCADE |
| `question_reviews.reviewer_id` | `users.id` | SET NULL |
| `question_asks.question_id` | `questions.id` | CASCADE |
| `question_asks.user_id` | `users.id` | SET NULL |
| `ai_reviews.question_id` | `questions.id` | CASCADE |

Deleting a question therefore removes its embeddings, concept links, and
review history. Concepts themselves are never deleted automatically, even if
no question references them.

---

## Extensions

| Extension | Purpose | Created by |
| --- | --- | --- |
| `vector` | `vector(1536)` column type and `<=>` cosine distance operator | Migration `608e29badd5f` |

The Docker image `pgvector/pgvector:pg17` ships the extension. On Supabase,
enable `vector` in the dashboard or let the migration create it.

---

## Migrations (Alembic)

### Layout

```
backend/
├── alembic.ini          # script_location, logging
└── alembic/
    ├── env.py           # Reads DATABASE_URL, imports models, sets target_metadata
    ├── script.py.mako   # Template for new revision files
    └── versions/        # One file per revision
```

`env.py` reads the connection string from the `DATABASE_URL` environment
variable, not from `alembic.ini`. All Alembic commands must be run from the
`backend/` directory with that variable set (loading `backend/.env` is enough
when running through `uv run` inside Docker; locally export it or use a
`.env`-aware shell).

### Revision history

Revisions in order from the first to the current head:

| Revision | Created | Summary |
| --- | --- | --- |
| `c73fa181a936` | 2026-08-08 | Create `questions` (`id`, `question`, `answer`) |
| `608e29badd5f` | 2026-08-09 | `CREATE EXTENSION IF NOT EXISTS vector` |
| `b89ba1041804` | 2026-08-09 | Create `question_embeddings` |
| `4ce2611e20d5` | 2026-08-09 | Add `created_at` / `updated_at` to `questions` |
| `4a29086da7e1` | 2026-08-09 | Add `type` and `chunk_index` to `question_embeddings` |
| `e9074ec4815a` | 2026-08-11 | Create `users` with unique email index |
| `19042706a040` | 2026-08-13 | Create `concepts`, `question_concepts`, `question_reviews`; add `status` / `source` to `questions` with status index |
| `2c62a31a9031` | 2026-08-14 | Add `language` to `questions` |
| `7f3b1c9d4e21` | 2026-08-16 | Add `retrieved_question_ids` to `questions` |
| `a1d2e3f4b5c6` | 2026-10-24 | Make `question_reviews.reviewer_id` nullable with `ON DELETE SET NULL` |
| `b2c3d4e5f6a7` | 2026-10-25 | Bilingual rows: `question`/`answer` become `question_ja`/`answer_ja` (`text`), add `*_en` and provenance columns, `original_language`, `question_embeddings.language`, `concepts.name_ja`/`name_en`, `question_reviews.language`. Downgrade deletes English-only rows. |
| `c8d9e0f1a2b3` | 2026-10-27 | Create `rate_limit_hits` for the Postgres-backed rate limiter |
| `d9e0f1a2b3c4` | 2026-10-27 | Google Sign-In: `users.hashed_password` nullable, add `auth_provider` and unique `google_sub`, provider check constraints. Downgrade deletes Google accounts. |
| `e0f1a2b3c4d5` | 2026-10-28 | Create `question_asks`: per-user ask history for signed-in callers |
| `f1a2b3c4d5e6` | 2026-10-28 | Add `question_asks.cache_hit` for the usage dashboard |
| `a2b3c4d5e6f7` | 2026-10-28 | Add `question_reviews.reason`: labelled reject/edit codes |
| `b3c4d5e6f7a8` | 2026-10-28 | Add generation metadata to `questions` (model, prompt version, mode, token usage) |
| `c4d5e6f7a8b9` | 2026-10-29 | Create `ai_reviews`; add `reviewer_kind` and `policy_name` to `question_reviews` |
| `d5e6f7a8b9c0` | 2026-10-30 | Create `ai_review_runs`: recorded reviewer runs with a single-running guard (**head**) |

The chain is linear with a single head. Verify with:

```bash
uv run alembic heads
uv run alembic history --verbose
```

### Common commands

Run these from `backend/`, or prefix with `docker compose exec backend`.

```bash
# Show the revision currently applied to the database
uv run alembic current

# Apply all pending migrations
uv run alembic upgrade head

# Roll back one revision
uv run alembic downgrade -1

# Roll back to a specific revision
uv run alembic downgrade 2c62a31a9031

# Create a new revision from model changes
uv run alembic revision --autogenerate -m "short description"

# Create an empty revision for hand-written SQL (extensions, data fixes)
uv run alembic revision -m "short description"
```

### Workflow for schema changes

1. Edit or add a model in `backend/physics_ai_tutor/models/` and export it
   from `models/__init__.py` so `env.py` picks it up.
2. Run `uv run alembic revision --autogenerate -m "..."` against a database
   that is already at `head`.
3. Open the generated file in `alembic/versions/` and review it. Autogenerate
   does not detect everything. In particular check:
   - `server_default` values for new `NOT NULL` columns on existing tables
     (the existing data needs a default or the upgrade fails).
   - `ondelete` behaviour on foreign keys.
   - Index changes and `Vector` column dimensions.
   - That `downgrade()` really reverses `upgrade()`.
4. Apply with `uv run alembic upgrade head`, then run `uv run alembic
   downgrade -1` and `upgrade head` once to prove the downgrade path works.
5. Run the backend test suite (`uv run pytest`).
6. Commit the model change and the migration file together.

Rules from `AGENTS.md` that apply here:

- Never modify the schema without a migration.
- Never modify the production database directly.
- Keep seed data reproducible.

### Migrations in CI and production

- CI (`.github/workflows/ci.yml`) runs `alembic upgrade head` against a fresh
  pgvector container before tests, so a broken migration fails the build.
- Production (Render backend, Supabase database) is migrated by running
  `uv run alembic upgrade head` with `DATABASE_URL` pointing at the Supabase
  session pooler URL (see `backend/.env.template`). Run it before deploying
  code that depends on the new schema.
- Prefer additive, backward-compatible migrations (add a nullable column or a
  column with a default first, backfill, then tighten) so the running
  backend keeps working while the migration is applied.

---

## Local Development

### Containers

`docker-compose.yml` starts two PostgreSQL instances:

| Service | Database | Host port | Purpose |
| --- | --- | --- | --- |
| `postgres` | `physics_ai_tutor` | 5432 | Development data, persisted in the `postgres_data` volume |
| `postgres-test` | `physics_ai_tutor_test` | 5433 | Ephemeral database used by `pytest` |

Both use user `physics` / password `physics`.

Connection strings:

```
# Development (from the host)
DATABASE_URL=postgresql+psycopg://physics:physics@localhost:5432/physics_ai_tutor

# Development (from inside the backend container)
DATABASE_URL=postgresql+psycopg://physics:physics@postgres:5432/physics_ai_tutor

# Tests (default in tests/conftest.py, override with TEST_DATABASE_URL)
TEST_DATABASE_URL=postgresql+psycopg://physics:physics@localhost:5433/physics_ai_tutor_test
```

Connect with `psql` for inspection:

```bash
docker compose exec postgres psql -U physics -d physics_ai_tutor
```

### Resetting the development database

```bash
docker compose down -v        # drops the postgres_data volume
docker compose up -d
docker compose exec backend uv run alembic upgrade head
docker compose exec backend uv run python -m physics_ai_tutor.database.seed
```

### Seed data

`seed.json` holds 144 entries: 21 hand-translated bilingual pairs plus 123
teacher-approved Q&A exported from production on 2026-10-30 (Japanese
only; the English side is machine translated on import). Refresh the
production part by exporting `questions` with `status = 'APPROVED'` again
after a review pass.

`backend/physics_ai_tutor/database/seed.py` loads
`backend/physics_ai_tutor/database/seed.json` and inserts each entry as an
`APPROVED` / `MANUAL` question with embeddings in every language. Entries
may be written either way:

```json
{"question": "速度ってなに？", "answer": "..."}
{"question_ja": "速度ってなに？", "answer_ja": "...",
 "question_en": "What is velocity?", "answer_en": "..."}
```

The first form is Japanese; its English side is machine translated during
the seed (`MACHINE`). The second form keeps the supplied English as a
`HUMAN` translation. Concept extraction and translation both call DeepSeek,
so the seed requires valid `OPENAI_API_KEY` and `DEEPSEEK_API_KEY` values;
translation failures are logged and the row is kept in one language.

The import is all-or-nothing. If any question text in the file already
exists in the database (or appears twice in the file), a
`DuplicateQuestionError` is raised and nothing is inserted. To add entries to
an already seeded database, import only the new rows through the admin
import endpoint, or reset the database first.

`seed.jsonl` in the same directory holds the same content in JSONL form and
is the format accepted by the admin import endpoint
(`POST /api/v1/questions/import`) and the "Upload" page in the admin UI.

### Creating an admin user

The database has no built-in accounts. After migrating, create an admin:

```bash
docker compose exec backend uv run python -m physics_ai_tutor.cli.create_user \
  --email admin@example.com --role admin
# You will be prompted for a password (8 to 128 characters).
```

Pass `--password` to skip the prompt (avoid this in shared shells; it ends up
in shell history).

### Backfilling translations

Rows that lack a language (data from before the bilingual schema, or rows
whose translation failed) can be filled in bulk:

```bash
docker compose exec backend uv run python -m physics_ai_tutor.cli.translate_missing --dry-run
docker compose exec backend uv run python -m physics_ai_tutor.cli.translate_missing
docker compose exec backend uv run python -m physics_ai_tutor.cli.translate_missing --language en --limit 50
```

The same operation is exposed to admins as `POST /api/v1/questions/translate`.

### `init_db.py`

`backend/physics_ai_tutor/database/init_db.py` calls `Base.metadata.create_all`.
It is a convenience for throwaway experiments only. Do not use it on a
database you intend to migrate: it creates tables without recording an
Alembic revision, so `alembic upgrade head` will later fail with "relation
already exists". Use Alembic for every real database.

### Test database behaviour

`backend/tests/conftest.py` builds the test schema with the real migrations.
Once per session it drops and recreates the `public` schema of the test
database and runs `alembic upgrade head`; between tests it truncates all
tables. Two dedicated tests in `tests/test_migrations.py` fail the suite if
the migration chain has more than one head or if the SQLAlchemy models
drift from what the migrations produce, so a forgotten migration is caught
locally, not only in CI.

The test database is wiped on every run, so isolation is handled
automatically:

- Unless `TEST_DATABASE_URL` is set, the database name is derived from the
  checkout path (`physics_ai_tutor_test_<hash>`), so several worktrees can
  share one `postgres-test` container without touching each other's data.
- The database is created on first use; no manual `CREATE DATABASE` needed.
- A PostgreSQL advisory lock is held for the whole session. A second pytest
  run against the same database aborts immediately instead of corrupting
  the first one.

Set `TEST_DATABASE_URL` explicitly to use a specific database (CI pins it
to `physics_ai_tutor_test`; `docker compose exec backend uv run pytest`
uses the in-network URL set in `docker-compose.yml`).

---

## Review dataset export

`physics_ai_tutor/cli/export_reviews.py` (and `GET /admin/reviews/export`)
emit one JSON object per `question_reviews` row, oldest first, with these
fields in order:

| Field | From | Notes |
| --- | --- | --- |
| `review_id`, `question_id` | ids | |
| `language` | `question_reviews.language` | Text the reviewer looked at or edited. |
| `source` | `questions.source` | `MANUAL`, `AI_GENERATED`, `RAG_RESULT`. |
| `generation_model`, `prompt_version`, `generation_mode` | `questions` | `null` for manual rows and rows generated before 2026-10-28. |
| `retrieved_question_ids` | `questions` | RAG grounding ids. |
| `concepts` | `question_concepts` | Names in `language`. |
| `question_before`, `answer_before`, `question_after`, `answer_after` | `question_reviews` | Equal for plain approvals. |
| `action`, `reason`, `comment` | `question_reviews` | `reason` is `null` for approvals and for rows before 2026-10-28. |
| `reviewer_kind`, `policy_name` | `question_reviews` | `human` for everything so far. |
| `reviewer_hash` | derived | HMAC-SHA256 of the reviewer id keyed with `JWT_SECRET_KEY`, first 16 hex chars; `null` when the reviewer account was deleted. No user id or e-mail is exported. |
| `reviewed_at` | `question_reviews.created_at` | ISO 8601. |
| `ai_verdict`, `ai_confidence`, `ai_reasons`, `ai_prompt_version`, `ai_reviewed_at` | `ai_reviews` | The latest AI verdict created *before* the human review (what the teacher could see); all `null` when there was none. Lets `review_metrics --from-file` reproduce the agreement report offline. |

The default start date is the **2026-10-28 data cutoff**: before it, rows
lack the correction diff ([07]), the reason code ([08]), and generation
metadata ([09]), so they would read as "approved unchanged, no reason,
unknown prompt". Pass `--all` (or `all=true`) to include them anyway.

---

## Cache and knowledge base

The `questions` table serves two purposes with different rules:

| Role | Rows used | Readers | Gate |
| --- | --- | --- | --- |
| Knowledge base | `APPROVED` | Public list, detail, search, related, RAG context | Teacher review |
| Answer cache | `APPROVED` and `UNREVIEWED` | `POST /api/v1/ai/ask` exact-text lookup before generating | None beyond "not rejected" |

The ask flow checks the cache first (tier 0, no API call). If an identical
question exists in the requested language, that answer is returned with its
status so the UI can label unreviewed answers. Otherwise it generates an
answer (DeepSeek), stores it as `UNREVIEWED`, and translates it in the
background. Because both languages are stored on the same row, a question
answered and approved in Japanese is served from cache to an English
student who asks the translated text, with no second generation.

## Operational Notes

- **Machine translations are not reviewed.** Review certifies the physics;
  a `MACHINE` translation inherits it and is shown to students with a
  "translated" label. Admins can filter by provenance to spot-check, and a
  human edit of a translation flips it to `HUMAN` so it is never regenerated.
- **Vector dimension is fixed at 1536** in both the `question_embeddings`
  and `concepts` tables. Switching to an embedding model with a different
  dimension requires a migration that alters the column type and a
  re-embedding of all rows. The `model` / `embedding_model` columns exist to
  make that migration selective.
- **`updated_at` is maintained by the ORM**, so raw SQL updates will not
  refresh it.
- **Deleting a reviewer keeps their reviews.** `question_reviews.reviewer_id`
  is set to `NULL` on user deletion, so the audit trail is preserved without
  blocking account removal.
- **Status filtering is application-side**: non-admin callers only ever
  receive `APPROVED` rows from the list, detail, exact-match, related, and
  search endpoints. RAG retrieval and context loading also use `APPROVED`
  rows only. There are no row-level security policies in PostgreSQL, so any
  new public endpoint must apply the same filter (see
  `PUBLIC_HIDDEN_STATUSES` in the questions router).
