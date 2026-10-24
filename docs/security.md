# Security Guide

This document describes the security model of Physics AI Tutor and the
practices contributors are expected to follow. It complements
[docs/api.md](api.md) (access rules per endpoint) and
[docs/database.md](database.md) (data model).

---

## Threat model in brief

- Students use the site anonymously. They can read approved content, run
  semantic search, and ask the AI. They must never see unreviewed or
  rejected content, and they must not be able to make the project pay for
  unbounded LLM usage.
- Admins (teachers) log in to manage content and users. Their sessions must
  be protected against theft and cross-site abuse.
- The backend holds third-party API keys and the database credentials.
  These must never reach the browser or the repository.

---

## Authentication and sessions

- Login is email + password. Passwords are hashed with Argon2id via
  `pwdlib`; plaintext is never stored or logged.
- A successful login sets a JWT in an **HttpOnly** cookie. JavaScript cannot
  read it, which removes the token from XSS reach.
- Cookie flags come from settings: `COOKIE_SECURE=true` in production
  (HTTPS only) and `SAME_SITE=lax` (or `strict`). With `lax`, cross-site
  POST requests do not carry the cookie, which is the primary CSRF defense.
  Do not set `SAME_SITE=none` unless a cross-site embed is really needed and
  an explicit CSRF token is added.
- Tokens are short-lived (`JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, 15 by default)
  and silently re-issued when close to expiry. On re-issue the user's role
  is re-read from the database, so a demoted or deleted account loses access
  within one token lifetime.
- Tokens carry `iss`, `iat`, `exp`, `jti`, `sub`, and `role`. Signature
  algorithm is fixed to `JWT_ALGORITHM` (HS256); the verifier does not
  accept `alg` from the token.
- There is no self sign-up. The first admin is created with the CLI; further
  accounts are created by admins through the API. An admin cannot delete
  their own account, which prevents locking everyone out by accident.

Secrets:

```bash
# Generate a JWT secret; 32 random bytes minimum
openssl rand -base64 32
```

Rotate `JWT_SECRET_KEY` if it is ever exposed. Rotation invalidates every
session at once, which is the intended effect.

---

## Authorization

- Two roles exist: `admin` and `user`. All write operations on questions and
  all user management require `admin` and are enforced server-side with the
  `require_admin` dependency. The frontend hides admin UI, but that is
  convenience, not security.
- Public read endpoints filter by status so non-admins only receive
  `APPROVED` questions. The filter lives in the questions router
  (`PUBLIC_HIDDEN_STATUSES`) and in the RAG and recommendation services.
  Any new endpoint that returns question content must apply it.
- IDs sent by the client (for example `retrieved_question_ids` on the AI
  endpoint) are re-validated against the database and their status is
  re-checked server-side.

---

## Input validation and output encoding

- All request bodies are Pydantic models with length limits, for example
  questions up to 1000 characters, answers up to 5000, AI prompts 5 to 200.
  Oversized or malformed input is rejected with 422 before reaching services.
- JSONL imports are parsed line by line; one bad line rejects the whole file
  with a per-line error list, and nothing is written.
- Answers are Markdown and are rendered in the browser with `react-markdown`,
  which escapes raw HTML by default. KaTeX and Mermaid run client-side on
  the Markdown source. Mermaid output is inserted as SVG; keep
  `securityLevel` at Mermaid's default (strict) if the initialization
  options are ever changed.
- Database access goes through SQLAlchemy with bound parameters. Keyword
  search uses `ILIKE` with parameters, not string concatenation. SQL errors
  return a generic 500; details go to the server log only.

---

## Browser hardening (frontend)

`frontend/next.config.ts` sets these headers on every response:

| Header | Value | Purpose |
| --- | --- | --- |
| `Content-Security-Policy` | `default-src 'self'`, `connect-src 'self' <API>`, `frame-ancestors 'none'`, `img-src 'self' data:`, inline scripts and styles allowed | Limits where scripts, styles, images, and API calls may come from |
| `X-Frame-Options` | `DENY` | Clickjacking |
| `X-Content-Type-Options` | `nosniff` | MIME sniffing |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Referrer leakage |
| `Permissions-Policy` | camera, microphone, geolocation disabled | Browser feature abuse |

`'unsafe-inline'` for scripts is currently required by the Next.js runtime
and the Mermaid/KaTeX renderers. Removing it with nonces is a known
improvement.

The backend CORS allow-list (`BACKEND_CORS_ORIGINS`) must contain only the
real frontend origins. Credentials are allowed, so a wildcard is never
acceptable.

---

## Abuse and cost control

The AI endpoint calls a paid LLM, so it is rate limited per client IP:

| Caller | Limits |
| --- | --- |
| Anonymous or `user` | 3 per minute, 10 per hour, 30 per day |
| `admin` | 3000 per day |

Login attempts are limited to 5 per minute and 20 per hour per IP to slow
credential stuffing.

Notes:

- The limiter is in-process memory. It resets on restart and is per
  instance. If the backend is ever scaled horizontally, move it to a shared
  store such as Redis.
- `TRUST_FORWARDED_FOR=true` reads the client IP from `X-Forwarded-For`.
  Only enable it behind a proxy you control (Render sets this header). If
  the backend is ever exposed directly, set it to `false`, otherwise clients
  can spoof their IP and bypass the limit.
- Exact-match lookup and semantic search run before any LLM call, and RAG
  answers are cached as questions, so repeated questions do not cost tokens
  twice.

---

## Secrets and configuration

- Never commit `backend/.env`, `frontend/.env.local`, or any file containing
  keys. Both are ignored by git; `.env.template` files hold placeholders only.
- Only variables prefixed `NEXT_PUBLIC_` are shipped to the browser. The
  backend URL is public by design; nothing else should carry that prefix.
- The production database URL uses Supabase's session pooler with a
  dedicated password. Do not reuse it locally.
- The SQLAlchemy engine is created with `hide_parameters=True`, so bound
  values (including hashed passwords and user text) are not echoed in error
  messages.
- Logs contain request method, path, status, user id, and action names. They
  do not contain tokens, passwords, or full question text by design; keep it
  that way when adding log lines.
- API documentation (`/docs`, `/redoc`, `/openapi.json`) is served only when
  `ENVIRONMENT=development`.

---

## Dependencies

Policy:

- Keep Next.js, React, and the Node.js runtime on currently supported
  versions. The project targets **Node.js 24 LTS** (`frontend/.nvmrc`,
  `engines` in `package.json`, `node:24-alpine` in the Dockerfile, and the
  CI workflow).
- `npm audit` must report zero vulnerabilities before merging. Transitive
  packages can be forced to a safe version with the `overrides` field in
  `package.json` (currently used to pin a single `katex` version for
  `rehype-katex`, `remark-math`, and `mermaid`).
- Python dependencies are locked in `backend/uv.lock`. Upgrade with
  `uv lock --upgrade` and run the full backend checks.
- Lockfiles are authoritative. Docker images and CI install with `npm ci`
  and `uv sync`, never with floating installs.

Routine check:

```bash
# Frontend
cd frontend
npm audit
npm outdated

# Backend
cd backend
uv lock --upgrade --dry-run
```

Upgrades to Next.js in particular should be applied promptly. Several past
advisories (cache poisoning, SSRF in image optimization, RCE in `use cache`)
were fixed only in patch releases.

---

## Database

- The application connects with a single role. Access control is enforced
  by the API layer; there are no row-level security policies. Do not expose
  the database to the public internet.
- Schema changes go through Alembic migrations only. Production is never
  edited by hand (see `AGENTS.md`).
- Deleting a question cascades to its embeddings, concept links, and review
  rows. Deleting a user keeps their review rows with `reviewer_id` set to
  `NULL`, so the audit trail of who approved what is not silently lost.
- Backups are Supabase's responsibility at the current scale. If the
  knowledge base grows, add a scheduled `pg_dump` of the `questions`,
  `concepts`, and `question_reviews` tables.

---

## Reporting a vulnerability

Please do not open a public issue for security problems. Email the
maintainer (see the GitHub profile of `k94-ishi`) with a description and,
if possible, reproduction steps. You will get an acknowledgement, and a fix
will be published before details are disclosed.

---

## Checklist for pull requests touching security-relevant code

- [ ] New public endpoint filters out non-`APPROVED` questions.
- [ ] New admin endpoint depends on `require_admin`.
- [ ] New request model has length limits on every string field.
- [ ] No secret, token, or raw user text is written to logs.
- [ ] `npm audit` and the CI workflow are green.
- [ ] Schema change ships with an Alembic migration and a passing
      `tests/test_migrations.py`.
