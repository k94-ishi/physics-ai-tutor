---
title: "[22] robots.txt: allow /privacy (currently Disallow: / blocks the consent-screen check)"
labels: [deploy, frontend, privacy]
milestone: M0 Deploy Google Sign-In
priority: P0
---

**Priority:** P0  **Milestone:** M0 — Deploy Google Sign-In

## Summary

`frontend/src/app/robots.ts` serves `Disallow: /` for all user agents, so
crawlers — including Google's privacy-policy check for the OAuth consent
screen — cannot fetch `/privacy` even though the page's own metadata allows
indexing ([01], commit 506e2be).

## Motivation

[01] made `/privacy` indexable at the page level, but robots.txt wins: a
crawler that honours it never requests the page, and the consent-screen
review may fail to verify the privacy policy URL. The rest of the site
should stay unindexed.

## Scope

- `robots.ts`: keep `disallow: "/"` as the general rule and add
  `allow: "/privacy"` ahead of it (Next's `MetadataRoute.Robots` accepts
  `rules: [{ userAgent: "*", allow: "/privacy", disallow: "/" }]`).
- Once [21] ships, `/help` likely wants the same treatment; note it there.

## Acceptance criteria

- [ ] `GET /robots.txt` contains `Allow: /privacy` and `Disallow: /`.
- [ ] Google's robots.txt tester (or a manual check of precedence rules)
      confirms `/privacy` is fetchable and `/` is not.

## Out of scope

- Opening any other route to indexing.

## Technical notes

One-file change plus a vitest asserting the returned object shape.

## Dependencies

- Blocked by: none
- Blocks: [02] (consent screen verification needs /privacy fetchable)

## Definition of done

- [ ] Frontend checks pass
- [ ] docs/security.md note about /privacy indexing mentions robots.txt
