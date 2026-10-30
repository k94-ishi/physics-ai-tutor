# Operator checklist (for the project owner)

Written 2026-10-31. Everything in the repository is implemented and tested;
what remains needs a human with console access, a teacher's judgement, or
production credentials. The steps are in dependency order - each phase
unblocks the next. Issue numbers are git-bug ids (`git bug bug show <id>`).

Rough effort: Phase 1 one evening, Phase 2 one careful hour, Phase 3 a few
minutes, Phase 4 ongoing (minutes per day), Phase 5 one hour once.

---

## Phase 1 - Decisions and judgement calls (no deployment yet)

### 1.1 Read the v2 answer prompt and the reviewer rubric (15 min)

```bash
cd backend
uv run python -m physics_ai_tutor.cli.show_prompts --family answer
uv run python -m physics_ai_tutor.cli.show_prompts --family ai_review
```

What you are checking: tone and wording a teacher would use, the scope
rule (what the model should decline), the "no calculus unless the student
used it" rule, the length targets. If you change any text:

1. edit `backend/physics_ai_tutor/core/prompt_library.yaml`,
2. bump that family's `version` (`v2` -> `v3`, `r1` -> `r2`),
3. run `uv run pytest tests/test_prompts.py` - it prints the new
   fingerprint to paste into `FAMILY_FINGERPRINTS`,
4. run the eval (Phase 5.2) before relying on the new prompt.

Issue [29] `84ff079` already lists the two changes the data asks for:
ban Mermaid diagrams, tighten scope to exclude chemistry / materials /
course-structure questions. Doing 1.1 and [29] together is the natural move.

### 1.2 Judge the seven flagged answers - issue [30] `4ef75f5` (30 min)

The AI reviewer says seven *published* answers contain physics errors;
two look clearly wrong to me (pendulum acceleration at the lowest point;
"仕事をされるとエネルギーが減る"). The issue lists all seven with the claims.
For each one, in the admin UI (`/admin/questions`, search by the question):

- if the AI is right: open **編集**, fix the text, click **保存して承認**,
  pick the reason (PHYSICS_ERROR etc.). This records a proper
  `EDIT_APPROVE` with a diff and a reason - exactly the data the project
  needs from now on.
- if the AI is wrong: leave the answer; add a line to the issue so the
  golden set keeps it as a known false positive.

You can do this on production today (it is the current code's edit flow),
or after Phase 2 if you prefer to do everything on the new version.

### 1.3 Pick a contact address for the privacy policy (5 min)

`frontend/src/app/privacy/page.tsx` has `CONTACT_URL` pointing at the
GitHub issue tracker. Google's consent-screen reviewers and parents expect
a monitored e-mail. Replace the constant with a `mailto:` or a real page,
adjust the `privacy.contact.*` strings if the wording should change, and
commit. (Issue [02] `43c6f95` has the note.)

---

## Phase 2 - Google Cloud and the first deployment of the new code

### 2.1 Google Cloud console - issue [02] `43c6f95` (30-45 min)

1. Create a project (e.g. `physics-ai-tutor`).
2. **OAuth consent screen**: External; app name; support e-mail; developer
   contact; authorized domain `pencil-net.com`; privacy policy URL
   `https://ai-tutor.pencil-net.com/privacy`; scopes `openid` and `email`
   only. (The page is reachable by crawlers: `robots.txt` allows it.)
3. Publish the consent screen to **In production**. With only
   non-sensitive scopes there should be no verification review; the
   console tells you if that changed.
4. **Credentials -> OAuth client ID -> Web application**. Authorized
   redirect URIs: your Render backend URL + `/api/v1/auth/google/callback`
   (and `http://localhost:8000/api/v1/auth/google/callback` for local use).
   Copy the client id and secret; they go only into Render env vars and
   your local `.env`, never into git.

### 2.2 Back up Supabase, then migrate - issue [03] `58210f7` (20 min)

Production is at Alembic revision `7f3b1c9d4e21`; head is `d5e6f7a8b9c0`.
That is **ten** migrations, including the bilingual rename of the
`questions` text columns, so do this deliberately:

1. Take a Supabase backup / snapshot (dashboard -> Database -> Backups, or
   `pg_dump`). Do not skip this.
2. Put the backend into a quiet moment (early morning JST is fine).
3. From your machine, with the production URL in the environment for this
   shell only:

   ```bash
   cd backend
   export DATABASE_URL='<production url>'
   uv run alembic current          # expect 7f3b1c9d4e21
   uv run alembic upgrade head     # ~seconds; the bilingual step rewrites questions
   uv run alembic current          # expect d5e6f7a8b9c0 (head)
   unset DATABASE_URL
   ```

4. If anything fails midway: `uv run alembic downgrade 7f3b1c9d4e21` is
   safe for every step except the bilingual one once English-only rows
   exist (there are none in production today), and you have the backup.

Deploy the backend **after** the migration, not before: the new code
expects the new columns.

### 2.3 Render environment variables (5 min)

Add to the backend service (names exactly as in `backend/.env.template`):

| Variable | Value |
| --- | --- |
| `GOOGLE_CLIENT_ID` | from 2.1 |
| `GOOGLE_CLIENT_SECRET` | from 2.1 |
| `GOOGLE_REDIRECT_URI` | `https://<render-backend-host>/api/v1/auth/google/callback` - must equal the console entry byte for byte |
| `FRONTEND_URL` | `https://ai-tutor.pencil-net.com` |
| `AI_REVIEW_ENABLED` | `false` for now (Phase 3 turns it on) |
| `AI_REVIEW_DAILY_CAP` | `200` (raise temporarily for the backlog, see 3.2) |
| `AI_REVIEW_MAX_TOKENS` | `3000` |

Confirm `COOKIE_SECURE=true` and note the current `SAME_SITE` value - you
need it for 2.5.

### 2.4 Deploy backend, then frontend (10 min)

Merge/push your branch as you normally do; Render and Vercel redeploy.
Watch the Render log for the first requests.

### 2.5 Smoke test (15 min) - tick these on the [03] issue

- [ ] Admin password login still works; `/admin/questions` loads and shows
      the new **AI判定** filter and **並び順** selects.
- [ ] `/privacy` renders; `robots.txt` shows `Allow: /privacy`.
- [ ] In a private window, **Googleでログイン** with a personal
      `@gmail.com`: you land on the home page, the header shows
      **自分の質問 / アカウント**, and `/admin/users` lists the account with
      provider Google.
- [ ] **Cross-domain cookie check**: right after the Google redirect, open
      the browser dev tools -> Network and confirm `GET /users/me` returns
      200. If it returns 401 and your frontend and backend are on different
      sites (`pencil-net.com` vs `onrender.com`), the cookie is being
      dropped by `SAME_SITE=lax`; the fix is a backend custom domain under
      `pencil-net.com`, not `SAME_SITE=none`.
- [ ] Ask the AI something off-topic (「英語の宿題を手伝って」): a polite
      refusal, and no new row in the admin queue.
- [ ] Ask the same physics question twice: second response says cached,
      and `/me/questions` shows both asks.
- [ ] `/admin/stats` loads (the agreement section says "n too small").

### 2.6 Tell the other sessions / worktrees

If other Claude sessions are still running on other worktrees, they share
the git-bug store and the test Postgres container; nothing else changes
for them. Do **not** run `git bug wipe` anywhere.

---

## Phase 3 - Turn on the AI reviewer and work the backlog

### 3.1 Enable inline review (2 min)

Set `AI_REVIEW_ENABLED=true` on Render and redeploy. From then on every
new AI answer gets a verdict in the background and shows an **AI:** badge
in the queue. Cost: one extra DeepSeek call per *generation* (never per
cache hit).

### 3.2 Review the 1,179-question backlog (one command per day, or raise the cap)

The backlog is far above the default daily cap of 200. Options:

- **Patient**: run once a day for about six days (ideally in DeepSeek's
  discount window, 01:30-09:30 JST):

  ```bash
  cd backend && export DATABASE_URL='<production url>'
  uv run python -m physics_ai_tutor.cli.review_pending --limit 200
  unset DATABASE_URL
  ```

- **Fast**: temporarily set `AI_REVIEW_DAILY_CAP=1500` on Render (and in
  your shell as `AI_REVIEW_DAILY_CAP=1500` before the command), run with
  `--limit 1200`, then put the cap back. Roughly 1,200 calls of ~2-3k
  tokens each.

Either way, the run is recorded (`GET /admin/ai-review/runs`), only one
can execute at a time, and a stuck run frees itself after 30 minutes.
Issue [26] `e0594f1` is the automated nightly version; until it exists this
is a manual command.

### 3.3 Decide what to do with the backlog itself

1,179 unreviewed answers are more than one teacher will read. After 3.2,
sort the queue by **AI確信度順** with filter **AI: 却下** and handle those
first (likely junk), then **AI: 承認** in bulk after spot checks. Issue
[18] (auto-reject) exists for later, once Phase 4 shows the AI's rejects
are trustworthy.

---

## Phase 4 - Review so the data becomes useful (ongoing)

Every review you do from now on is a labelled example for the evaluator,
*if* it is done through the review actions:

- **却下** -> pick a reason in the dialog (required).
- **Edit then 保存して承認** -> the dialog asks the reason; the diff is
  recorded. Do **not** use plain **保存** for corrections you would like
  counted - it records nothing in the history.
- **承認** -> one click, no reason needed.

Markdown/Mermaid clean-ups count too: use 保存して承認 with reason
FORMATTING. (This is exactly what was missing from the 2026-08 history.)

After roughly **30 reviews on AI-reviewed questions**, `/admin/stats`
shows real agreement numbers instead of "n too small". The numbers that
matter: **reject precision** (gates auto-reject) and the **calibration
table** (which confidence bucket is trustworthy).

---

## Phase 5 - Keep the evaluation honest

### 5.1 GitHub secret for the Prompt Eval workflow (5 min, optional)

Repository -> Settings -> Secrets -> Actions -> `DEEPSEEK_API_KEY`. Then
**Actions -> Prompt Eval -> Run workflow** runs the golden set against the
committed baseline without a database. Without the secret, the dry-run
step still validates the set.

### 5.2 After any prompt change (10 min + ~70 DeepSeek calls)

```bash
cd backend
uv run python -m physics_ai_tutor.cli.eval_prompts --verbose    # compare with baseline
# if the change is intended and the numbers look right:
uv run python -m physics_ai_tutor.cli.eval_prompts --save-baseline
git add eval/ && git commit -m "Pin eval baseline for <versions>"
```

Exit code 1 means exact agreement or reject precision dropped more than
0.05 - look at the `[DIFF]` lines with `why:` before deciding. Two
identical runs differ by about 3 verdicts of 69, so re-run once if you are
near the threshold.

### 5.3 Grow the golden set from your new reviews (quarterly)

```bash
uv run python -m physics_ai_tutor.cli.export_reviews --out reviews.jsonl
```

Pick clear cases (both agreements and your corrections), convert them to
the `golden.jsonl` schema (`backend/eval/README.md`), keep APPROVE / EDIT
/ REJECT roughly balanced, and re-pin the baseline. Reviews made after
2026-10-28 carry real reason codes, unlike the 57 production cases that
are in the set today.

### 5.4 Refresh the seed data occasionally

After a review pass, export the approved questions again and replace the
production part of `backend/physics_ai_tutor/database/seed.json` (the
first 21 entries are the hand-translated pairs - keep them).

---

## What is intentionally *not* in this list

- Redis, a second backend instance, Batch APIs: not needed at this scale
  (DeepSeek has no Batch API anyway; checked 2026-10-30).
- Auto-reject / auto-approve ([18], [19]): only after Phase 4 shows >= 95 %
  agreement in the confidence bucket a policy would act on.
- Pushing git-bug refs to GitHub: the tracker is local by design; `git bug
  push` would publish it. Leave it local unless you decide otherwise.
