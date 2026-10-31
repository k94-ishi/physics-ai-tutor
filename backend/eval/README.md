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
  edits; `p-reject-*` are rejected answers. **The verdict is the teacher's;
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
