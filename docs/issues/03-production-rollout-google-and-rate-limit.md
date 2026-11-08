---
title: Production rollout: migrations, env vars, and cross-domain cookie check for Google Sign-In
labels: [deploy, ops, backend]
milestone: M0 Deploy Google Sign-In
priority: P0
---

**Priority:** P0  **Milestone:** M0 — Deploy Google Sign-In

## Summary

Apply the two pending migrations to Supabase, set the new Render env vars,
and verify the Google callback cookie flow works with the real Vercel and
Render domains before announcing the login to students.

## Motivation

Two schema changes (`rate_limit_hits`, Google columns on `users`) and four
new settings ship together. The callback sets the session cookie during a
top-level redirect on the backend domain, which is a different path from the
existing fetch-based login and has not been exercised in production.

## Scope

- [ ] `alembic upgrade head` against Supabase **before** deploying the
      backend (revisions `c8d9e0f1a2b3`, `d9e0f1a2b3c4`). Confirm
      `alembic current` afterwards.
- [ ] Render env vars: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`,
      `GOOGLE_REDIRECT_URI`, `FRONTEND_URL=https://ai-tutor.pencil-net.com`.
      Confirm `COOKIE_SECURE=true` and the current `SAME_SITE` value.
- [ ] Cross-domain check: if the frontend and backend are on different
      sites (e.g. `pencil-net.com` vs `onrender.com`), the access cookie set
      by the callback is only sent on later `fetch` calls if `SAME_SITE=none`
      is already in use. Verify `GET /users/me` returns 200 right after the
      redirect. If it does not, the fix is a backend custom domain on
      `pencil-net.com`, not weakening cookie flags.
- [ ] Rate limiter sanity: after deploy, `rate_limit_hits` receives rows;
      an anonymous 4th generation in an hour returns 429; a cached answer
      does not.
- [ ] Smoke test: password admin login still works; Google login creates a
      `users` row with `auth_provider='google'`; the admin user list shows it.
- [ ] Watch Render logs for `Google login rejected` and `state_mismatch`
      during the first days.

## Acceptance criteria

- [ ] All checklist items above ticked with the date and who verified.

## Out of scope

- Any code change; if the cookie check fails, open a separate issue.

## Technical notes

Rollback: `alembic downgrade -1` twice removes both migrations; the Google
downgrade deletes Google-only accounts, so take a Supabase backup first.

## Dependencies

- Blocked by: #02
- Blocks: announcing the feature to students

## Definition of done

- [ ] `docs/development.md` deployment notes updated with anything learned
