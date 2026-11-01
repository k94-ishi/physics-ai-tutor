# Golden evaluation set

`golden.jsonl` holds hand-labelled Q&A pairs for the offline prompt
regression check (`physics_ai_tutor.cli.eval_prompts`). Each line:

```json
{"id": "g01", "language": "ja", "question": "...", "answer": "...",
 "expected_verdict": "APPROVE|EDIT|REJECT", "expected_reasons": ["..."],
 "note": "why this label is correct"}
```

Two kinds of cases (66 total as of 2026-11-01):

- `g*` (13): labelled **by construction** - the APPROVE answers are correct
  and well-formatted, and every EDIT/REJECT case was written with exactly
  one deliberate defect (see `note`).
- `p-*` (53): taken from the production review history (teacher decisions
  of 2026-08, texts as of 2026-10-21). `p-approve-*` are teacher-approved
  answers; `p-edit-*` are the *pre-edit* texts of substantive teacher
  edits; `p-reject-*` are rejected answers. Ids are stable and never
  renamed, so a case can carry a verdict its prefix no longer matches:
  `p-approve-15/26/194/768` are EDIT cases since 2026-11-01, when the
  teacher corrected those answers in production and their stored pre-fix
  texts became true edits. **The verdict is the teacher's;
  the reason code was inferred from the diff** (the old history stored no
  reasons), so reason overlap is a weak signal on these cases.

Four production cases (`p-reject-1070`, `p-reject-47`, `p-reject-25`,
`p-reject-37`) were **removed** on 2026-11-01: the teacher confirmed they
were rejected with no recorded reason in the service's initial phase, so
their REJECT labels were not real judgements and were mis-measuring the
reviewer. They are physics questions and can come back once they have been
re-reviewed with a real verdict - do not re-add them as REJECT.

Keep expanding it with reviews made after 2026-10-28, which carry real
reason codes; keep the verdict balance roughly even.

Known exceptions in the production history (owner's decision 2026-11-01:
keep the rows as they are, but never treat them as real edits when
sampling or measuring):

- `question_reviews` **#104** (question 807, 2026-08-16): the edit only
  removed `**` markers to work around the CommonMark CJK rendering bug
  fixed in [36]; the text was never wrong.
- `question_reviews` **#12** (question 10, 2026-08-15): mostly the same
  workaround (spaces inserted before closing `**`) plus one glyph change.

Do not sample either into the golden set as an EDIT case, and exclude
them from any "how often did the teacher edit" analysis.

EDIT vs REJECT is genuinely fuzzy (e.g. a calculus-heavy answer could be
either); that is fine. The check compares against a *baseline* of the same
prompts, so what matters is drift, not absolute scores. Note that DeepSeek
at temperature 0 is not bit-reproducible: two back-to-back runs of the
69-case set differed on 3 verdicts (exact agreement 60.9 % vs 63.8 %), so
treat changes inside the tolerance as noise and re-run before concluding. Baselines live here
as `baseline-<answer_version>-<reviewer_version>.json` and are written by
`--save-baseline` after a run a human has eyeballed.

Each baseline records the `set_sha256` it was measured on; `eval_prompts`
warns when the set has changed since.

| baseline | measured on | status |
| --- | --- | --- |
| `baseline-v2-r1.json` | the set before the [30] notes landed | stale hash; historical reference only |
| `baseline-v3-r2.json` | the set before p-approve-15/26/194/768 became EDIT | stale hash; understates the prompts, since four cases were labelled APPROVE that the teacher had in fact corrected |
| `baseline-v4-r3.json` | the current 66-case set | **current** |

Do not compare across these files as if they were runs of one experiment:
the prompts *and* the set differ. In particular the v4/r3 jump in reject
recall (0.231 -> 0.778) is partly the prompt fix and partly the removal of
four cases that had been rejected without a reason (see above).

`--save-baseline` re-runs the whole set, so pinning costs another ~66
calls. v4/r3 was measured twice: exact agreement 66.7 % then 72.7 %,
publish agreement 95.5 % then 93.9 %, with reject precision (87.5 %) and
recall (77.8 %) identical in both. The pinned file deliberately carries the
*lower* observation of each varying metric, so that an unchanged prompt
does not trip the gate on run noise alone; it is not a verbatim copy of
either run's output.
