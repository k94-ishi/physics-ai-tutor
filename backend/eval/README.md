# Golden evaluation set

`golden.jsonl` holds hand-labelled Q&A pairs for the offline prompt
regression check (`physics_ai_tutor.cli.eval_prompts`). Each line:

```json
{"id": "g01", "language": "ja", "question": "...", "answer": "...",
 "expected_verdict": "APPROVE|EDIT|REJECT", "expected_reasons": ["..."],
 "note": "why this label is correct"}
```

The starter set (12 cases, 2026-10-30) is labelled **by construction**: the
APPROVE answers are correct and well-formatted, and every EDIT/REJECT case
was written with exactly one deliberate defect (see `note`). **Expanding it
to 50-100 teacher-verified cases is an open curation task**: export real
reviews (`export_reviews`), pick diverse cases a teacher confirms, convert
to this schema, and keep the verdict balance roughly even.

EDIT vs REJECT is genuinely fuzzy (e.g. a calculus-heavy answer could be
either); that is fine. The check compares against a *baseline* of the same
prompts, so what matters is drift, not absolute scores. Baselines live here
as `baseline-<answer_version>-<reviewer_version>.json` and are written by
`--save-baseline` after a run a human has eyeballed.
