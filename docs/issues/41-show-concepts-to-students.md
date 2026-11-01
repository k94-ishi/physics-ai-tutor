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
