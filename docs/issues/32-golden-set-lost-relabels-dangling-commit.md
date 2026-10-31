---
title: "[32] Bug: issue [30]'s golden-set relabels exist only in a dangling commit; branch and tracker disagree"
labels: [bug, eval, ai-review]
milestone: M4 Partial automation and regression safety
priority: P1
---

**Priority:** P1  **Milestone:** M4 — Partial automation and regression safety

## What happened

Two parallel sessions resolved [30] `4ef75f5` differently and only one
landed on a branch:

- Commit `01c6d16` ("Record the teacher's [30] verdicts in the golden set;
  pin v3-r2 baseline") relabelled the pre-fix texts of q15/q26/q194/q768
  from APPROVE to EDIT and pinned a v3/r2 baseline with exact agreement
  60.9 %. The [30] close comment and a [29] `84ff079` comment cite this
  commit — but it is reachable from **no branch** (dangling object).
- Commit `5e713f0` (on main) updated only the four false-positive notes
  (45/54/178/848) and left q15/q26/q194/q768 as `expected_verdict: APPROVE`.
- Commit `eb14a4a` then pinned `eval/baseline-v3-r2.json` with exact
  agreement 58.0 % against this un-relabelled set.

So the tracker describes a golden set and baseline that do not exist in the
repository, and two different "first v3/r2 baselines" circulate (58.0 % in
git, 60.9 % in the tracker).

## What should have happened

One golden set, one pinned baseline, and tracker comments that cite
reachable commits.

## Scope

- Recover the relabels from `01c6d16` (the object still exists:
  `git show 01c6d16 -- backend/eval/golden.jsonl`) or redo them from the
  review export: pre-fix texts of q15/q26/q194/q768 become EDIT with the
  production reasons.
- Re-run `eval_prompts --save-baseline` so `baseline-v3-r2.json` matches the
  corrected set (its `set_sha256` must equal the new `golden.jsonl` hash).
- `baseline-v2-r1.json` was pinned before `5e713f0` edited the set, so its
  `set_sha256` is already stale; note in `eval/README.md` which set each
  baseline was measured on.
- Add a comment to [30] `4ef75f5` pointing at the commit that actually
  landed, so the audit trail is honest.

## Acceptance criteria

- [ ] `golden.jsonl` on the branch carries the EDIT relabels for
      q15/q26/q194/q768.
- [ ] `baseline-v3-r2.json.set_sha256` equals `shasum -a 256 golden.jsonl`.
- [ ] [30]'s comments no longer point at an unreachable commit without
      saying so.

## Definition of done

- [ ] Backend checks pass; `eval_prompts --verbose` runs clean against the
      re-pinned baseline
