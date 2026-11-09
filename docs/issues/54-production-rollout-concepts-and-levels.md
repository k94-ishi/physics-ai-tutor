---
title: "[54] Production rollout: English concept names and difficulty levels (owner, when production is reachable)"
labels: [deploy, ops, owner, i18n]
milestone: M1 Student value
priority: P1
---

**Priority:** P1  **Milestone:** M1 — Student value

## Summary

Production's concepts carry Japanese names only, and no question has a
difficulty rating. Both are missing because production is still at
Alembic revision `7f3b1c9d4e21`; the code that fills them already exists.
This issue is the ordered list of owner steps; nothing here needs new code.
On hold: the owner cannot touch production yet (2026-11-09).

## Why the data is missing

- `concepts.name_en` was added by migration `b2c3d4e5f6a7` (2026-10-25),
  which production has not run, so production's concepts table still has
  one `name` column.
- Levels come from concept extraction (`backfill_levels`, checklist 5.3a);
  `seed.json` has them only for local stacks.

## Steps (details in docs/operator-checklist.md)

1. **Back up Supabase** (checklist 2.2 step 1). Do not skip.
2. **Migrate to head** (checklist 2.2): `alembic current` should print
   `7f3b1c9d4e21`, then `upgrade head`, then `current` prints the head.
   This creates `name_en` (empty for existing concepts) and the level columns.
   If [55] has landed by then, head also includes its concept-term tables.
3. **Deploy backend, then frontend** (checklist 2.4); smoke test (2.5).
4. **Run `backfill_levels`** in the discount window (checklist 5.3a),
   repeated until it prints "backfill done". It re-extracts every approved
   QA's concepts under the current prompt, which returns both language
   names, so this fills most English names *and* the two difficulty levels.
   Cost: one DeepSeek call per approved question.
5. **Remaining gaps fill themselves**: since [53], a student view of a QA or
   concept still missing a language queues one background translation per
   row/concept (APPROVED only, once each).
6. **Check**:
   - `/admin/manage/levels` lists rated rows (expect all approved rows).
   - Open a few questions with `?lang=en`: no Japanese text or chips.
   - Repeat [52]'s procedure on a fresh production sample of 30.

## Acceptance criteria

- [ ] Production at Alembic head; backup taken first.
- [ ] Every APPROVED question has both levels after the backfill.
- [ ] English concept names present for the extracted concepts; an English
      student sees no Japanese on a question page.

## Dependencies

- Blocked by: owner access to production
- Related: [03] (same migration step), [52] (production sample), [53], [55]

## Log

### 2026-11-10 - [55] landed

Head is now `e2f3a4b5c6d7` (concept senses). Step 4's `backfill_levels`
re-extracts under the new matching, which also splits senses the old rule
had merged; tune `CONCEPT_SENSE_MATCH_THRESHOLD` first ([55] open point).
Then run `split_merged_concepts --dry-run` to see what is left, and fix
stragglers in `/admin/manage/concepts`.
