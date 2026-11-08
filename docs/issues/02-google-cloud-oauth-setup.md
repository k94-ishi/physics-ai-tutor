---
title: Set up the Google Cloud OAuth client and consent screen
labels: [deploy, ops]
milestone: M0 Deploy Google Sign-In
priority: P0
---

**Priority:** P0  **Milestone:** M0 — Deploy Google Sign-In

## Summary

Create the Google Cloud project, consent screen, and OAuth client that the
backend's `/auth/google/*` endpoints expect.

## Motivation

The code is merged but disabled until `GOOGLE_CLIENT_ID`,
`GOOGLE_CLIENT_SECRET`, and `GOOGLE_REDIRECT_URI` exist. This is manual
console work with a few decisions that should be recorded.

## Scope

- [ ] Create a Google Cloud project (e.g. `physics-ai-tutor`).
- [ ] OAuth consent screen: user type **External**, app name, support e-mail,
      developer contact, authorized domain `pencil-net.com`, privacy policy
      URL from #01, scopes `openid` and `email` only.
- [ ] Move the consent screen from *Testing* to *In production*. With only
      non-sensitive scopes no verification review should be required; confirm
      in the console, since Google changes this.
- [ ] Create an OAuth client of type **Web application** with authorized
      redirect URIs for local (`http://localhost:8000/api/v1/auth/google/callback`)
      and production (the Render backend URL + `/api/v1/auth/google/callback`).
      The value must match `GOOGLE_REDIRECT_URI` byte for byte.
- [ ] Store the client secret only in Render env vars and the local `.env`;
      never in the repo.
- [ ] Record the project id and who owns it in `docs/development.md`.

## Acceptance criteria

- [ ] A personal `@gmail.com` account can sign in on the production site and
      lands on the home page with role `user`.
- [ ] A school Workspace account that is blocked shows Google's "Access
      blocked" page, and the login page's hint explains what to do.

## Out of scope

- Workspace admin approval for specific schools (each school's decision).

## Technical notes

See `docs/development.md` → "Google Sign-In setup". `prompt=select_account`
is already set so students can switch to a personal account.

## Dependencies

- Blocked by: #01
- Blocks: #03

## Definition of done

- [ ] Console settings documented; no secrets committed
