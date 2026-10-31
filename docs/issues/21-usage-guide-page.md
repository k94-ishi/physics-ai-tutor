---
title: "[21] Add a usage guide page (/help)"
labels: [feature, frontend, docs]
milestone: M1 Student value
priority: P3
---

**Priority:** P3  **Milestone:** M1 — Student value

## Summary

A public `/help` page (Japanese and English) explaining how to use the site:
searching the knowledge base, asking the AI, what the review statuses mean,
logging in with Google, and the ask limits.

## Motivation

Students arrive with no explanation of the search-before-ask flow, why an
answer is labelled "not yet reviewed", why a Google login raises their
allowance, or why a school account can be blocked. A short guide reduces
confused asks and support mail. Useful, but it blocks nothing, so it ranks
below the deployment and review-data work.

## Scope

- Static page `frontend/src/app/help/page.tsx`, strings in the i18n layer,
  both languages.
- Sections: what the site is; search first, ask when nothing fits; what the
  AI modes do; what UNREVIEWED / approved labels mean (a teacher checks
  answers); signing in with Google and the ask limits per tier; the school
  Workspace "Access blocked" case and using a personal account; where the
  privacy policy is.
- Keep numbers (ask limits) in one place: reuse or mirror the values from
  the rate-limit documentation rather than hard-coding them in prose twice.
- Link from the header (next to the login link) and from the login page.
- Screenshots optional; text first.

## Acceptance criteria

- [ ] `/help` renders in both languages without logging in.
- [ ] Header links to it; login page links to it.
- [ ] The described limits match `api/dependencies.py`.

## Out of scope

- Teacher/admin manual (separate issue if wanted).
- Interactive onboarding or tooltips.

## Technical notes

Same pattern as the privacy page ([01]): client page using `useLanguage`,
no API calls.

## Dependencies

- Blocked by: none (update the limits text if they change)
- Blocks: none

## Definition of done

- [ ] Frontend: `npm run lint`, `tsc --noEmit`, `npm test`, `npm run build` pass
- [ ] Login/header links present in both languages
