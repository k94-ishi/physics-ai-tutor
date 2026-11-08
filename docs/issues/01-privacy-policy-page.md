---
title: Add a privacy policy page (/privacy)
labels: [deploy, privacy, frontend]
milestone: M0 Deploy Google Sign-In
priority: P0
---

**Priority:** P0  **Milestone:** M0 — Deploy Google Sign-In

## Summary

Add a public `/privacy` page (Japanese and English) describing what the app
stores about a signed-in student and how to have it deleted.

## Motivation

Google's OAuth consent screen cannot be published without a privacy policy
URL, so this blocks Google Sign-In in production. The app also now stores
e-mail addresses of minors, which deserves a plain statement regardless.

## Scope

- Static page under `frontend/src/app/privacy/page.tsx`, strings in the i18n
  layer.
- Content: operator, what is stored (e-mail, Google subject id, role,
  timestamps, questions asked, rate-limit counters by IP or account), why
  (login, abuse control, improving the knowledge base), what is *not*
  collected (no profile, no avatar, no Google data beyond `openid email`),
  third parties (Google for sign-in, DeepSeek and OpenAI receive question
  text, Render/Vercel/Supabase host the service), retention, how to request
  deletion (link to #04 once it exists; e-mail contact until then), contact.
- Link from the login page's student card and from the footer.
- `robots` metadata may allow indexing of this page even though the rest of
  the site is `noindex`.

## Acceptance criteria

- [ ] `/privacy` renders in both languages without logging in.
- [ ] Login page links to it next to the Google button.
- [ ] The text matches what the code actually stores (`users`,
      `rate_limit_hits`, `questions`).

## Out of scope

- Terms of service (can share the page later if needed).
- In-app account deletion (#04).

## Technical notes

Plain server component; no API calls. Keep the copy short enough that a high
school student will read it.

## Dependencies

- Blocked by: none
- Blocks: #02 (consent screen needs the URL)

## Definition of done

- [ ] Frontend: `npm run lint`, `tsc --noEmit`, `npm test`, `npm run build` pass
- [ ] `docs/security.md` links to the page
