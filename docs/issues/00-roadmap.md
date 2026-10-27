---
title: "Roadmap: from Google Sign-In to AI-assisted review"
labels: [epic, roadmap]
milestone: M0 Deploy Google Sign-In
priority: P0
---

Last revised 2026-10-28. Issues are tracked locally with git-bug; this epic
links every issue and records the priority order and the findings behind it.
Update this issue (edit the first comment) when the order changes.

---

## Where the project is

- Students can read approved Q&A, search semantically, and ask the AI.
  Since 2026-10-27 they can sign in with Google for a larger allowance;
  admins keep e-mail + password.
- Every AI answer is saved as `UNREVIEWED`, served from cache to anyone
  asking the identical question, and waits for a teacher to approve, edit,
  or reject it. The review history (`question_reviews`) stores before/after
  text, action, reviewer, language, and an optional comment.
- Rate limiting is Postgres-backed; cache hits are free.

## Goal of the next phases

Turn the human review history into the training and evaluation signal for
an AI reviewer, and automate the low-risk parts of the queue while a teacher
stays the ground truth. In order: make the data worth learning from, add an
advisory AI reviewer, measure it against humans, then let it act on narrow,
audited policies.

---

## Phases

### M0 — Deploy Google Sign-In (this week)

| # | Issue | Priority |
| --- | --- | --- |
| #01 | Privacy policy page `/privacy` | P0 |
| #02 | Google Cloud OAuth client and consent screen | P0 |
| #03 | Production rollout: migrations, env vars, cross-domain cookie check | P0 |
| #04 | Student account self-deletion | P1 |

### M1 — Student value

| # | Issue | Priority |
| --- | --- | --- |
| #05 | Student question history tied to the review loop | P1 |
| #06 | Admin usage dashboard from `rate_limit_hits` | P2 |

### M2 — Review data foundation

Everything here changes what gets *recorded*; each week it is not shipped is
a week of reviews that cannot be used later.

| # | Issue | Priority |
| --- | --- | --- |
| #07 | Bug: "Save and approve" loses the correction diff | P1 |
| #08 | Structured review reasons on reject and edit | P1 |
| #09 | Generation metadata on AI questions (model, prompt version, tokens) | P1 |
| #10 | Answer prompt v2: scope guardrail, uncertainty, curriculum, versioning | P1 |
| #11 | Review dataset export (JSONL) | P2 |
| #12 | Schema for AI reviews (`ai_reviews`, `reviewer_kind`) | P2 |

### M3 — AI-assisted review (advisory only)

| # | Issue | Priority |
| --- | --- | --- |
| #13 | AI pre-review: rubric prompt and background job | P2 |
| #14 | Show the AI suggestion in the admin queue; sort and prefill | P2 |
| #15 | Agreement metrics: AI verdict vs human verdict, calibration | P2 |
| #16 | Few-shot grounding from similar past human reviews | P3 |

### M4 — Partial automation and regression safety

| # | Issue | Priority |
| --- | --- | --- |
| #17 | Golden evaluation set and offline prompt regression check | P2 |
| #18 | Policy: auto-reject off-topic with audit sample and kill switch | P3 |
| #19 | Policy: auto-approve grounded, high-confidence answers | P3 |
| #20 | Versioned prompt rollouts with A/B comparison | P3 |

---

## Priority order (what to pick up next)

1. **#01 → #02 → #03** — nothing else matters until students can log in.
2. **#07** — a one-afternoon fix; until it lands, every teacher correction is
   recorded as a no-op `APPROVE`.
3. **#10** — the prompt has no topic boundary; with self-service login the
   knowledge base must not absorb off-topic exchanges. Also fixes small
   prompt defects (see findings).
4. **#08, #09** — reasons and generation metadata; together with #07 they
   make the review history a labelled dataset from day one.
5. **#05** — the student-facing payoff of logging in.
6. **#04** — self-service deletion; the privacy page can point to e-mail
   until then.
7. **#06, #11, #12** — observability and plumbing for the AI reviewer.
8. **#13 → #14 → #15** — advisory reviewer, UI, measurement.
9. **#17** — regression gate before any policy is allowed to act.
10. **#16, #18, #19, #20** — only after #15 shows ≥ 95 % agreement in the
    confidence bucket a policy would act on.

---

## Findings behind the ranking

From reading `core/prompts.py`, `services/question_service.py`,
`services/rag_service.py`, `services/concept_service.py`, and the admin UI
on 2026-10-27.

**Review system**

- `question_reviews` is a good base: before/after text per language,
  action, reviewer (kept after account deletion), timestamp.
- The edit page's "Save and approve" sends `PUT` then `APPROVE`, so the row's
  before equals after. `EDIT_APPROVE`, which captures the diff, is not used by
  the UI (#07).
- `comment` is never sent by the UI and there is no reason code, so the
  history records *what* changed but not *why* (#08).
- Bulk approve is one click with no reason; fine for seed data, risky for a
  growing AI queue. The AI pre-review (#13, #14) is meant to make bulk actions
  informed rather than remove them.
- No `reviewer_kind`; an AI verdict has nowhere to live without polluting
  the human history (#12).
- Review history is per question only; there is no dataset view (#11).

**Prompts**

- Answer generation records no model or prompt version; concept extraction
  does (`CONCEPT_EXTRACTION_PROMPT_VERSION = "v2"`). Outcomes across prompt
  changes cannot be compared (#09).
- No scope rule: any 5–200 character string is answered, saved as
  `UNREVIEWED`, and cached for identical future asks (#10).
- No uncertainty rule and no curriculum anchor (物理基礎 / 物理); "high
  school" alone invites university methods (#10).
- Japanese prompt is missing a "。" between the first two sentences; the
  English prompt never mentions the Japanese curriculum, so JA and EN answers
  to the same question can diverge in level (#10).
- RAG suffix and context labels are sound; `RAG_MIN_SCORE = 0.5` and only
  `APPROVED` grounding are the right defaults and are reused by #19.
- DeepSeek calls use the provider's default temperature; eval runs (#17)
  should pin it.

**Why not fine-tune**

The review history will be hundreds of rows, not hundreds of thousands.
In-context examples retrieved by similarity (#16) and a calibrated rubric
(#13, #15) use that data fully; fine-tuning would not, and would add a
training pipeline to operate. Revisit if the corpus passes ~10k reviewed
items.
