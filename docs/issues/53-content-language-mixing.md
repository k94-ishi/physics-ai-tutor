---
title: "[53] Bug: Japanese text appears in English mode on the question page"
labels: [bug, i18n, frontend, backend, student]
milestone: M1 Student value
priority: P1
---

**Priority:** P1  **Milestone:** M1 — Student value

## What happened

In English mode a question page shows Japanese QAs and concept names.
The detail endpoint translates a missing language on first view, but four
other paths silently fall back to the original language:

- `/questions/{id}/related` (`recommendation_service`)
- `/questions/{id}/prerequisites`, including `gaps`
- concept names (`Concept.display_name` falls back to the other language)
- `retrieved_questions` ("referenced questions")

The home-page list already excludes such rows for students
(`only_with_language`); these paths do not.

Frontend: `QuestionDetail` fetches once before `useLanguage().resolved`,
i.e. in `ja`, then again in the stored language - the pattern
`docs/development.md` forbids.

## What should have happened

Students only ever read the language they chose.

## Fix (owner's decision 2026-11-09: translate, store the result)

- For non-admins, rows lacking `lang` are left out of the response *and*
  queued for one background translation (`translate_missing_languages`,
  APPROVED rows only, de-duplicated so one row is translated once). The
  next view shows them. Cost is one DeepSeek call per row, ever; the
  result lives in the database.
- Concept names missing in `lang` are left out and their name is filled
  by a background translation the same way.
- Admins keep the fallback (as the admin list does).
- Frontend: wait for `resolved` before fetching; on language switch,
  clear related/prerequisite state and close the preview.
- `docs/security.md`: list the new translation call site and its bound
  (APPROVED rows only, once per row).

## Definition of done

- [ ] pytest: an English request never returns Japanese text on the four
      paths; a missing row is translated once and appears next time
- [ ] vitest: one fetch per load in the resolved language
- [ ] Backend and frontend checks pass; `docs/api.md` updated

## Log

### 2026-11-09 - implemented

- Backend: `prepare_for_response(strict_language=...)` drops concept names
  and referenced questions lacking the language; related and prerequisite
  services drop such rows *before* ranking/slicing (so a student still
  gets the full count from readable rows) and report their ids. The
  router queues them to `background_translation_service` (APPROVED only,
  in-flight de-duplication, own session, never raises). Detail, list and
  exact-match pass the same flag for non-admins. Admins keep the fallback.
- Prerequisites: an untranslated definer is treated as "no definer yet",
  so its concept shows as a gap until the translation lands.
- Concept names: hidden, **not translated** - there is no name-translation
  step; names come from concept extraction, which returns both languages.
  Locally all 790 concepts have both names. Owner to decide whether a
  name-translation prompt (new prompt family, version + fingerprint) is
  worth it.
- Frontend: `QuestionDetail` and `QuestionList` wait for
  `useLanguage().resolved`; a language switch clears the previous
  language's related/prerequisite results and closes the preview.
- Tests: `tests/test_language_strict.py` (6); vitest "fetches once, in the
  stored language" (fails without the guard, verified). pytest 492,
  ruff, mypy, lint, tsc, vitest 159, build: all pass.
- Left open for the owner to verify in the UI.
