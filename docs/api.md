# API Reference

The backend exposes a versioned REST API under `/api/v1`. In development the
interactive OpenAPI UI is available at `http://localhost:8000/docs`; it is
disabled when `ENVIRONMENT` is not `development`.

This page is a map of the endpoints and their access rules. Request and
response bodies are defined by the Pydantic models in
`backend/physics_ai_tutor/schemas/` and shown in full in the OpenAPI UI.

---

## Authentication

- Two login methods issue the same HttpOnly JWT cookie: email + password
  (admins, and users created by an admin) and Google Sign-In (students,
  self-service). The browser sends the cookie automatically; no
  `Authorization` header is used.
- Access tokens expire after `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`. Tokens close
  to expiry (within `JWT_REFRESH_THRESHOLD_MINUTES`) are transparently
  re-issued on authenticated requests.
- Roles are `admin` and `user`. Only `admin` can manage content and users.

Access levels used below:

| Level | Meaning |
| --- | --- |
| Public | No cookie required |
| User | Any logged-in account |
| Admin | Account with role `admin` |

---

## Language

Every question has text in Japanese and English on the same row. Read
endpoints take `lang` (`ja` default, or `en`) and return the text in that
language; the response also carries `language` (the language actually
served), `provenance` (`ORIGINAL`, `HUMAN`, `MACHINE`), `original_language`,
`available_languages`, and `texts` with both language blocks. For non-admin
callers, list results only include rows that have text in `lang`; detail
requests for a row that lacks `lang` are translated on the fly.

Write endpoints accept either `{"question", "answer", "language"}`
(language defaults to `ja`) or the explicit
`{"question_ja", "answer_ja", "question_en", "answer_en"}` shape. A
missing language is machine translated at creation.

## Health

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/health` | Public | Liveness check |
| GET | `/api/v1/db-health` | Public | Runs a trivial query against the database |

## Auth

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/auth/providers` | Public | Which login methods are available (`{"password": true, "google": bool}`) |
| POST | `/api/v1/auth/login` | Public | Email + password login; sets the access cookie. Rate limited per IP (5/min, 20/hour). Rejects Google-only accounts. |
| GET | `/api/v1/auth/google/login` | Public | Redirects the browser to Google with an anti-CSRF `state` cookie. 503 when Google Sign-In is not configured. |
| GET | `/api/v1/auth/google/callback` | Public | Exchanges the code, creates the account on first sign-in (role `user`), sets the access cookie, and redirects to `FRONTEND_URL`. On failure redirects to `FRONTEND_URL/login?error=google_failed` or `?error=account_exists`. |
| POST | `/api/v1/auth/logout` | Public | Clears the access cookie |

## Users

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/users/me` | User | Current user's id, email, role |
| PUT | `/api/v1/users/me/password` | User | Change own password |
| GET | `/api/v1/users/me/profile` | Authenticated | Own account details (email, role, `auth_provider`, registration date) for the account page |
| DELETE | `/api/v1/users/me` | Authenticated | Self-service account deletion; clears the session cookie. Refused (400) for admins, who must be removed by another admin. Review history survives with `reviewer_id` set to `null`; ask history is unlinked the same way. |
| GET | `/api/v1/users/me/questions` | Authenticated | The caller's ask history (`page`, `size`, `lang`), newest first: question text in `lang` (falling back to the original), current `status`, `provenance`, and `asked_at`. Rejected questions come back with `answer: null`. |
| GET | `/api/v1/users` | Admin | List users |
| POST | `/api/v1/users` | Admin | Create a user or admin |
| GET | `/api/v1/users/{user_id}` | Admin | Get one user |
| DELETE | `/api/v1/users/{user_id}` | Admin | Delete a user. Their review records are kept with `reviewer_id` set to `null`. Admins cannot delete themselves. |

## Questions

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/questions?lang=` | Public | Paginated list with optional keyword (matches any language) and status filter. Non-admins only see `APPROVED` rows that have text in `lang`. |
| GET | `/api/v1/questions/exact-match?question=&lang=` | Public | Look up a question by exact text in the `lang` column. Non-admins only match `APPROVED` rows. |
| GET | `/api/v1/questions/{id}?lang=` | Public | Question detail with concepts and referenced questions in `lang`. 404 for non-admins unless `APPROVED`. |
| GET | `/api/v1/questions/{id}/related?lang=` | Public | Concept- and embedding-based recommendations, compared within `lang` |
| POST | `/api/v1/questions/search` | Public | Semantic similarity search within one language. Body: `{"query": str, "limit": int, "language": "ja" or "en"}`. Returns rows with cosine `distance`. |
| GET | `/api/v1/questions/{id}/reviews` | Admin | Review history of a question |
| GET | `/api/v1/admin/stats` | Admin | Usage dashboard data (`days` 1–90, default 14): per-day generations (all callers), signed-in asks, cache hits, distinct users; plus unreviewed count, median backlog age, and distinct anonymous IP buckets in the last 24h. 429 counts are deliberately not collected (recording them would add an unthrottled write on the rejection path). |
| POST | `/api/v1/questions` | Admin | Create an `APPROVED` / `MANUAL` question |
| PUT | `/api/v1/questions/{id}` | Admin | Edit question text and answer; embeddings are regenerated |
| DELETE | `/api/v1/questions/{id}` | Admin | Delete a question and its embeddings, concept links, and reviews |
| POST | `/api/v1/questions/{id}/review` | Admin | Apply `APPROVE`, `EDIT_APPROVE`, or `REJECT` and record a review row. `REJECT` and `EDIT_APPROVE` require a `reason` code (`PHYSICS_ERROR`, `MATH_ERROR`, `INCOMPLETE`, `OFF_TOPIC`, `TOO_ADVANCED`, `UNCLEAR`, `FORMATTING`, `LANGUAGE`, `DUPLICATE`, `OTHER`); `OTHER` additionally requires a `comment`. Body may include `language` (which text was reviewed or edited; defaults to the original). Edit-approve regenerates a machine-made counterpart. The admin UI's "Save and approve" sends `EDIT_APPROVE` with the edited text (one request per changed language, machine-translated languages first), so the review row holds the correction as a before/after diff. |
| POST | `/api/v1/questions/translate` | Admin | Fill missing languages by machine translation. Body: `{"question_ids": [int]}`. |
| POST | `/api/v1/questions/bulk-review` | Admin | Review many questions with one action. Bulk `REJECT` requires one `reason` applied to every row; bulk `APPROVE` needs none. |
| POST | `/api/v1/questions/bulk-delete` | Admin | Delete many questions |
| POST | `/api/v1/questions/import` | Admin | Upload a JSONL file (`multipart/form-data`, field `file`) with optional `status`, `source`, and `language` (default for legacy rows) form fields. All-or-nothing on duplicates. |
| POST | `/api/v1/questions/concepts/extract` | Admin | Re-run concept extraction for the given question ids |

JSONL import format, one object per line, in either shape:

```json
{"question": "速度ってなに？", "answer": "..."}
{"question_ja": "速度ってなに？", "answer_ja": "...", "question_en": "What is velocity?", "answer_en": "..."}
```

## AI

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/ai/ask` | Public | Answer a question. Body: `{"question": str, "language": "ja" or "en", "mode": "RAG" or null, "retrieved_question_ids": [int] or null}`. Response: `{"answer", "language", "cached", "question_id", "status"}`. |

The flow, in order:

1. **Cache**: if a non-rejected row already has this exact question text in
   `language`, its answer is returned with `cached: true` and the row's
   `status`. Unreviewed answers are reused this way; the UI must label them.
2. **Generate** with the system prompt for `language`. `mode` controls the
   pipeline: `null` is a direct LLM call (source `AI_GENERATED`); `"RAG"`
   retrieves `APPROVED` questions by similarity within `language` (or loads
   the given `retrieved_question_ids`, re-validated server-side) and builds a
   context prompt (source `RAG_RESULT`).
3. If the model declines the question as outside high-school physics (a
   leading `[OFF_TOPIC]` sentinel), the polite refusal is returned with
   `question_id: null` and nothing is saved, translated, or cached; the ask
   still counts against the rate limit. Otherwise the answer is saved as
   `UNREVIEWED` in `language`, and the other language is machine translated
   in a background task after the response is sent.
4. For a signed-in caller, the ask is recorded in `question_asks` (on cache
   hits too) so `GET /users/me/questions` can show their history. Anonymous
   asks are not recorded.
5. The saved row records how it was generated: model, answer prompt version,
   mode (`DIRECT`/`RAG`), and token usage. Admin question responses include
   this as a `generation` object; public responses always return
   `generation: null`.

Rate limits (anonymous callers are bucketed by IP, signed-in callers by
account):

| Caller | Bucket | Limits |
| --- | --- | --- |
| Anonymous | IP | 3 per hour, 10 per day |
| `user` | account | 10 per hour, 30 per day |
| `admin` | account | 3000 per day |

Counters are stored in the `rate_limit_hits` table, so they survive backend
restarts. Cached answers do not consume quota; only requests that trigger a
generation are counted. `TRUST_FORWARDED_FOR` controls whether the
`X-Forwarded-For` header is used to identify anonymous clients.

---

## Content visibility

Every public read endpoint applies the same rule: callers without an admin
session only receive questions whose status is `APPROVED`. `UNREVIEWED` AI
answers and `REJECTED` rows are visible to admins only. The one exception is
the ask-flow cache: an unreviewed answer is returned again to anyone who asks
the identical question, carrying `status: "UNREVIEWED"` so the UI shows the
same "not yet reviewed" label as for a fresh answer. Machine-translated text
carries `provenance: "MACHINE"` so the UI can label it as translated from
reviewed content.

## Error responses

| Status | When |
| --- | --- |
| 401 | Missing or invalid cookie on a protected endpoint |
| 403 | Logged in but not `admin` on an admin endpoint |
| 404 | Question or user not found (or hidden by status for non-admins) |
| 409 | A question with identical text already exists |
| 422 | Validation error, including malformed JSONL lines on import |
| 429 | Rate limit exceeded |
| 503 | Embedding, LLM, or concept extraction provider failed |
| 500 | Database error (details are logged, not returned) |
