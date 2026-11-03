---
title: "[52] Evaluate the LLM difficulty ratings against the teacher (validation gate for [38]/[42])"
labels: [data-quality, eval, owner]
milestone: M1 Student value
priority: P1
---

**Priority:** P1  **Milestone:** M1 — Student value

## Summary

[40] gives every QA two advisory levels (physics, math, 0-4) rated by
the LLM. Before [38] ranks prerequisites or [42] draws a grid on them,
the teacher checks that the numbers mean what the rubric says. This
issue is the procedure and the place to record the result. It runs on
the local 144-row seed corpus first (no production change needed); the
same procedure is repeated on a production sample after the backfill.

## What "good enough" means

The model does not agree with itself exactly: two independent runs on
the same 144 rows matched exactly on ~70 % of rows per axis and within
±1 on ~99 % ([40] log, 2026-11-03). So:

- **Within ±1 >= 90 %** on both axes: the scale is usable; go ahead
  with [38]/[42], correcting individual rows as you meet them.
- **Mean offset** (LLM − teacher) beyond ±0.5 on an axis: the model is
  systematically high or low; fix the rubric wording for that axis and
  re-rate, do not correct rows one by one.
- Within ±1 **below 90 %**, or adjacent levels indistinguishable in your
  own ratings: collapse the scale (e.g. 0-2) before building on it.

Exact agreement is reported but is not the gate.

## Procedure (about one hour for 30 QAs)

1. Open `/admin/manage/levels` on the local stack and log in as an admin.
   The rubric from [40] is pinned at the top of the page.
2. Press **ランダムに30件選ぶ** once. The 30 ids are stored in the
   browser; the filter switches to **評価用サンプル**. Do not re-draw
   unless you want a fresh sample.
3. Tick **LLMの評価を隠す** so the model's numbers are hidden while you
   rate (blind rating).
4. For each row: click the question text to open the full question,
   answer and concepts. Ask one thing: *what does a reader need to know
   to follow this answer?* Pick physics and math in the **自分**
   columns. Ratings are saved in the browser as you go; you can stop
   and resume.
5. When all 30 have both numbers, untick the blind box. Cells differing
   by one turn amber, by two or more red. Switch the filter to **LLMと
   食い違うもの** and read the red rows; note why you disagree (rubric
   unclear? model wrong? your own slip?).
6. Press **一致率をMarkdownでコピー** and paste the table into the Log
   below with the date and 2-3 lines of observations, including any
   rubric wording you want changed.
7. Apply the gate above and write the decision in the Log: go / fix
   rubric and re-rate / collapse the scale.
8. Optional: for rows where you are sure, press **教員の修正として保存**
   so the database carries your number. Not needed for the evaluation
   itself.

## After the gate passes

- Production: migrate, deploy, run `backfill_levels` (checklist 5.3a),
  then repeat steps 1-7 on production with a fresh sample of 30. The
  seed corpus is high-school material; production has a wider spread.
- Close this issue with both tables in the Log; [38] and [42] unblock.

## Acceptance criteria

- [ ] Agreement table for the local 30-row sample recorded in the Log
- [ ] Decision recorded (go / fix rubric / collapse scale)
- [ ] Agreement table for a production sample recorded after the backfill

## Dependencies

- Blocked by: nothing (local); production part needs checklist Phase 2
- Blocks: [38] ranking, [42] grid
- Related: [40]
