# Golden evaluation set

`golden.jsonl` holds hand-labelled Q&A pairs for the offline prompt
regression check (`physics_ai_tutor.cli.eval_prompts`). Each line:

```json
{"id": "g01", "language": "ja", "question": "...", "answer": "...",
 "expected_verdict": "APPROVE|EDIT|REJECT", "expected_reasons": ["..."],
 "note": "why this label is correct"}
```

Two kinds of cases (69 total as of 2026-10-30):

- `g*` (12): labelled **by construction** - the APPROVE answers are correct
  and well-formatted, and every EDIT/REJECT case was written with exactly
  one deliberate defect (see `note`).
- `p-*` (57): taken from the production review history (teacher decisions
  of 2026-08, texts as of 2026-10-21). `p-approve-*` are teacher-approved
  answers; `p-edit-*` are the *pre-edit* texts of substantive teacher
  edits; `p-reject-*` are rejected answers. Ids are stable and never
  renamed, so a case can carry a verdict its prefix no longer matches:
  `p-approve-15/26/194/768` are EDIT cases since 2026-11-01, when the
  teacher corrected those answers in production and their stored pre-fix
  texts became true edits. **The verdict is the teacher's;
  the reason code was inferred from the diff** (the old history stored no
  reasons), so reason overlap is a weak signal on these cases.

Keep expanding it with reviews made after 2026-10-28, which carry real
reason codes; keep the verdict balance roughly even.

EDIT vs REJECT is genuinely fuzzy (e.g. a calculus-heavy answer could be
either); that is fine. The check compares against a *baseline* of the same
prompts, so what matters is drift, not absolute scores. Note that DeepSeek
at temperature 0 is not bit-reproducible: two back-to-back runs of the
69-case set differed on 3 verdicts (exact agreement 60.9 % vs 63.8 %), so
treat changes inside the tolerance as noise and re-run before concluding. Baselines live here
as `baseline-<answer_version>-<reviewer_version>.json` and are written by
`--save-baseline` after a run a human has eyeballed.

Each baseline records the `set_sha256` it was measured on; `eval_prompts`
warns when the set has changed since. Both committed baselines predate the
2026-11-01 relabelling ([32]) and so carry stale hashes:

| baseline | measured on | status |
| --- | --- | --- |
| `baseline-v2-r1.json` | the set before the [30] notes landed | stale; kept as the historical v2/r1 reference point |
| `baseline-v3-r2.json` | the set before p-approve-15/26/194/768 became EDIT | stale; the numbers understate the prompts, since four cases were labelled APPROVE that the teacher had in fact corrected |

Neither was re-measured, because [33] bumps both prompt versions and so
writes a fresh `baseline-v4-r3.json` anyway - one eval run instead of two.
Do not compare across these files: a baseline is only meaningful against a
run of the same prompt versions on the same set.
