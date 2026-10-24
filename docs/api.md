# API Reference

The backend exposes a versioned REST API under `/api/v1`. In development the
interactive OpenAPI UI is available at `http://localhost:8000/docs`; it is
disabled when `ENVIRONMENT` is not `development`.

This page is a map of the endpoints and their access rules. Request and
response bodies are defined by the Pydantic models in
`backend/physics_ai_tutor/schemas/` and shown in full in the OpenAPI UI.

---

## Authentication

- Login sets an HttpOnly JWT cookie. The browser sends it automatically; no
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

## Health

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/health` | Public | Liveness check |
| GET | `/api/v1/db-health` | Public | Runs a trivial query against the database |

## Auth

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/login` | Public | Email + password login; sets the access cookie. Rate limited per IP (5/min, 20/hour). |
| POST | `/api/v1/auth/logout` | Public | Clears the access cookie |

## Users

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/users/me` | User | Current user's id, email, role |
| PUT | `/api/v1/users/me/password` | User | Change own password |
| GET | `/api/v1/users` | Admin | List users |
| POST | `/api/v1/users` | Admin | Create a user or admin |
| GET | `/api/v1/users/{user_id}` | Admin | Get one user |
| DELETE | `/api/v1/users/{user_id}` | Admin | Delete a user. Their review records are kept with `reviewer_id` set to `null`. Admins cannot delete themselves. |

## Questions

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/questions` | Public | Paginated list with optional keyword and status filter. Non-admins only see `APPROVED` rows. |
| GET | `/api/v1/questions/exact-match?question=` | Public | Look up a question by exact text; used before calling the AI. Non-admins only match `APPROVED` rows. |
| GET | `/api/v1/questions/{id}` | Public | Question detail with concepts and referenced questions. 404 for non-admins unless `APPROVED`. |
| GET | `/api/v1/questions/{id}/related` | Public | Concept- and embedding-based recommendations |
| POST | `/api/v1/questions/search` | Public | Semantic similarity search. Body: `{"query": str, "limit": int}`. Returns rows with cosine `distance`. |
| GET | `/api/v1/questions/{id}/reviews` | Admin | Review history of a question |
| POST | `/api/v1/questions` | Admin | Create an `APPROVED` / `MANUAL` question |
| PUT | `/api/v1/questions/{id}` | Admin | Edit question text and answer; embeddings are regenerated |
| DELETE | `/api/v1/questions/{id}` | Admin | Delete a question and its embeddings, concept links, and reviews |
| POST | `/api/v1/questions/{id}/review` | Admin | Apply `APPROVE`, `EDIT_APPROVE`, or `REJECT` and record a review row |
| POST | `/api/v1/questions/bulk-review` | Admin | Review many questions with one action |
| POST | `/api/v1/questions/bulk-delete` | Admin | Delete many questions |
| POST | `/api/v1/questions/import` | Admin | Upload a JSONL file (`multipart/form-data`, field `file`) with optional `status` and `source` form fields. All-or-nothing on duplicates. |
| POST | `/api/v1/questions/concepts/extract` | Admin | Re-run concept extraction for the given question ids |

JSONL import format, one object per line:

```json
{"question": "速度ってなに？", "answer": "..."}
```

## AI

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/ai/ask` | Public | Generate an answer with DeepSeek. Body: `{"question": str, "mode": "RAG" | null, "retrieved_question_ids": [int] | null}`. The answer is saved as an `UNREVIEWED` question. |

`mode` controls the pipeline:

- `null`: direct LLM call with the system prompt only; saved with source `AI_GENERATED`.
- `"RAG"`: retrieves `APPROVED` questions by similarity (or loads the given
  `retrieved_question_ids`, re-validated server-side), builds a context
  prompt, then calls the LLM; saved with source `RAG_RESULT` and the ids used.

Rate limits per client IP:

| Caller | Limits |
| --- | --- |
| Anonymous or `user` | 3 per minute, 10 per hour, 30 per day |
| `admin` | 3000 per day |

The limiter is in-process memory, so limits reset on backend restart and are
not shared across instances. `TRUST_FORWARDED_FOR` controls whether the
`X-Forwarded-For` header is used to identify the client.

---

## Content visibility

Every public read endpoint applies the same rule: callers without an admin
session only receive questions whose status is `APPROVED`. `UNREVIEWED` AI
answers and `REJECTED` rows are visible to admins only. The answer returned
by `POST /api/v1/ai/ask` is shown to the asker inline and is not reachable by
id until an admin approves it.

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
