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

- [x] Agreement table for the local 30-row sample recorded in the Log
- [x] Decision recorded (go / fix rubric / collapse scale)
- [ ] Agreement table for a production sample recorded after the backfill

## Dependencies

- Blocked by: nothing (local); production part needs checklist Phase 2
- Blocks: [38] ranking, [42] grid
- Related: [40]

## Log

### 2026-11-04 Review

- summary

| axis | n | exact | within ±1 | mean offset (LLM − me) |
| --- | --- | --- | --- | --- |
| physics_level | 30 | 57% | 97% | 0.40 |
| math_level | 30 | 70% | 97% | 0.13 |

- 30 result

(Physics, Math)

| Question                                   | LLM-P | LLM-M | Me-P  | Me-M |
| ------------------------------------ | --- | --- | --- | --- |
| #150止まっている物体にも速度はあるの？                | 1   | 0   | 1   | 0   |
| #151速度と加速度はどう違うの？                    | 1   | 0   | 1   | 0   |
| #152等速直線運動ではなぜ加速度が0なの？               | 1   | 0   | 1   | 0   |
| #160投げ上げたボールが最高点にいるとき、加速度は0？         | 1   | 0   | 1   | 0   |
| #164なぜ物理では現実にありえないような運動を考えるの？        | 1   | 0   | 0   | 0   |
| #170ベクトルってなに？                        | 1   | 1   | 1   | 1   |
| #172放物運動ってなに？                        | 1   | 2   | 1   | 1   |
| #177剛体のつり合いには、どんな条件が必要なの？            | 3   | 3   | 2   | 2   |
| #180斜面上で物体が転倒する条件は、どうやって調べるの？        | 1   | 2   | 1   | 2   |
| #183様々な運動の単元では、どんな運動を扱うの？            | 2   | 2   | 1   | 2   |
| #189なぜドーナツ型の物体は重心が物体の外側(空洞部分)にくるの？   | 1   | 1   | 1   | 2   |
| #190力のモーメントは、力の大きさが同じでも変わることがあるの？    | 1   | 1   | 2   | 1   |
| #195平面内を運動する物体の加速度は、どんなときに0になるの？     | 1   | 2   | 1   | 2   |
| #198運動量保存の法則ってなに？                    | 2   | 1   | 1   | 2   |
| #202衝突の前後で、運動量とエネルギーはどちらも保存されるの？     | 2   | 1   | 2   | 2   |
| #209向心力ってなに？                         | 2   | 2   | 1   | 1   |
| #217なぜ遠心力は「見かけの力」と呼ばれるの？             | 3   | 2   | 2   | 0   |
| #219万有引力の法則ってなに？                     | 2   | 1   | 2   | 1   |
| #227気体の状態方程式ってなに？                    | 2   | 1   | 2   | 1   |
| #231熱力学第二法則ってなに？                     | 3   | 1   | 2   | 1   |
| #232ホイヘンスの原理ってなに？                    | 3   | 1   | 2   | 0   |
| #250なぜレンズは中心と端で厚さが異なるように作られているの？     | 2   | 1   | 1   | 0   |
| #261作用反作用の法則は、どんな実験で確かめられるの？         | 1   | 1   | 1   | 1   |
| #264なぜ作用反作用の力は打ち消し合わないの？             | 2   | 0   | 1   | 0   |
| #265運動方程式が具体的に使われる場面を教えて             | 2   | 2   | 1   | 2   |
| #269弾性力による位置エネルギーってなに？               | 2   | 1   | 2   | 1   |
| #273力学的エネルギーの学習は、落下運動の学習とどうつながっているの？ | 2   | 1   | 2   | 1   |
| #274波ってなに？                           | 3   | 1   | 1   | 1   |
| #275波長ってなに？                          | 1   | 1   | 1   | 1   |
| #278固定端の反射と自由端の反射はどう違うの？             | 3   | 2   | 3   | 2   |

**My evaluation is based not on the levels of QAs theirselvs, but on what a reader need to know to follow these QAs.**

### 2026-11-04 - checked; decision: GO

Recomputed all six statistics from the 30-row table: they match the
summary exactly. Against the gate:

- within ±1 is 97 % on both axes (gate: >= 90 %) - the scale is usable;
- mean offset +0.40 (physics) and +0.13 (math) are inside ±0.5 - no
  rubric rewrite required.

**Decision: GO.** [38] ranking and [42] grid may build on the axes.
Individual rows get corrected as they are met (the page's
教員の修正として保存 button).

One pattern to watch, not act on yet: the physics axis leans high, and
the lean is concentrated at level 3. Every LLM physics-3 in the sample
except #278 came down under the teacher's reading (#177 剛体のつり合い
3→2, #217 遠心力 3→2, #231 熱力学第二法則 3→2, #232 ホイヘンスの原理
3→2, #274 波ってなに？ 3→1). The model appears to rate by topic area
(waves, entropy = "classical abstraction") where the teacher rates by
what this answer's reader needs - a plain-language introduction to an
abstract topic is not a 3. Math shows no such concentration (6 high,
3 low). If the production sample shows the same physics lean at or
beyond +0.5, the fix is one sentence in the physics-3 wording of the
extraction prompt, then re-rate; do not correct rows one by one.

Remaining: the production sample after the rollout and backfill
(checklist Phase 2, then 5.3a, then steps 1-7 here on a fresh sample).

### 2026-11-04 - "wave phase" removed from the physics-3 examples

Owner's call after the review above: the example invited exactly the
observed lean (波ってなに？ and ホイヘンスの原理 rated 3 by topic).
Removed from the extraction prompt, the issue [40] table and the
review-page rubric; still v6 (nothing has been rated under v6 yet), no
re-evaluation - the production sample stays the test of the wording.
