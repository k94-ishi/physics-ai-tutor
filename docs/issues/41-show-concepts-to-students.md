---
title: "[41] Show concepts to students as clickable chips; concepts are the map, not admin metadata"
labels: [feature, frontend, student]
milestone: M1 Student value
priority: P2
---

**Priority:** P2  **Milestone:** M1 — Student value

## Summary

Concepts are extracted for every question and are **already in the public
question payload** (`GET /questions/{id}` returns them to everyone), but
only the admin queue renders them. Students never see the one piece of
structure the app builds for them. Show the concepts on the student
question page as chips; clicking a chip lists other questions that share
the concept.

## Motivation

The owner's model (2026-11-01): the related-QA graph is the scaffolding
that lets a student climb from an advanced answer down to its
prerequisites. Concepts are the nodes of that graph. A student who meets
微分方程式 in an answer should be able to tap the concept and see every
QA about it — this is the simplest working form of the ladder, available
long before smarter ranking ([38]) lands.

## Scope

- Question detail page: concept chips under the answer (both languages,
  reuse the admin chip styling as a shared component).
- Chip click → a list of APPROVED questions sharing the concept. Needs a
  small backend filter (`GET /questions?concept=...` or a dedicated
  endpoint reusing `question_concept_repository`); public, so only
  APPROVED rows.
- Empty result ("you are the first here") handled honestly with an
  invitation to ask.

## Acceptance criteria

- [ ] A student sees the concepts on an approved question's page and can
      navigate to other questions sharing one.
- [ ] Unreviewed/rejected questions never appear in the chip's list.

## Out of scope

- Difficulty-aware ordering of the chip's list ([40]/[42]).

## Dependencies

- Blocked by: none (data already public)
- Related: [38], [39]

## Definition of done

- [ ] Frontend and backend checks pass; vitest for the chip navigation
- [ ] docs/api.md updated if a filter/endpoint is added

## Log

### 2026-11-09 - reopened: concept filter and concepts on related cards

Owner's feedback: students can reach a concept list only by clicking a
chip; there is no way to *choose* a concept. The admin page's "concept"
select only means extracted / not extracted, and it filters the current
page client-side, so its counts are wrong.

Follow-up scope:

- Backend: public `GET /api/v1/concepts?lang=&q=&limit=` returning concept
  names in `lang` with the number of linked questions (APPROVED only for
  non-admins). No schema change. Repository/service/router, pytest
  (visibility rule, `lang`, prefix search), `docs/api.md`.
- Frontend: shared `ConceptFilter` (search box with suggestions) that
  writes `?concept=`; clearing removes it. Used on the home page above the
  list in both tabs, and on `/admin/questions`, sent to the server with
  the other filters. The old select is renamed "Concept extraction" and
  moves server-side so counts are right.
- Concepts on each related QA card (question page, "Read these first"
  block and the related list; not grid cells): compact `ConceptChips`
  variant (about 3 chips + "+N", no heading). The card is one `<button>`
  today and links cannot nest in it, so the question text becomes the
  preview button and the chips sit beside it.

Acceptance:

- [ ] A student can pick a concept from a searchable list on the home page.
- [ ] An admin can filter the queue by a concept; totals and pagination are correct.
- [ ] Each related card shows its concepts; clicking one opens the concept list,
      clicking the question opens the preview.

### 2026-11-10 - tag chips on cards instead of a search box (owner)

- After trying the concept search box ([55]), the owner preferred chips on
  every card: the home-page cards and the related / "Read these first"
  cards on the question page now show up to 5 tags (+ "more"), as links
  beside the card link (never nested). The search box is removed; the
  `GET /concepts` endpoint stays for the "which meaning?" chooser.
- Naming: the UI calls them **タグ / tag**; the heading "この回答に出てくる
  概念 / Concepts in this answer" is removed. Code keeps `concept`.
- Admin-queue concept filter (by tag) is still open.
- Tests: QuestionList cards (chips outside the link, 5 + more, no search
  box), QuestionDetail related-card chips and no heading. vitest 162.
