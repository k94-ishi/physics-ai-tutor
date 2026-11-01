# Issue tracker (files are the system of record)

Since 2026-11-02 issues are managed **here, as files** (owner's decision).
The git-bug store is a **read-only archive** of everything up to that date,
including all discussion comments; browse it with `git bug bug` /
`git bug bug comment <id>`, and never write to it.

## Workflow

- **Open an issue**: add `NN-short-slug.md` with the usual front matter
  (title, labels, milestone, priority), then add its row here with status
  `open`. `NN` is the next unused number below.
- **Close / reopen**: flip the Status cell here. Status lives only in this
  file; the issue files carry the body.
- **Progress notes**: append a dated `## Log` section inside the issue file.
- Tracks [45]-[48] are ordered queues of references; keep their order
  current instead of duplicating detail.

## Status

| # | Status | File | Title | git-bug archive |
| --- | --- | --- | --- | --- |
| 00 | open | 00-roadmap.md | Roadmap: from Google Sign-In deployment to AI-assisted review | 80a4ad6 |
| 01 | closed | 01-privacy-policy-page.md | Add a privacy policy page (/privacy) | 614e32a |
| 02 | closed | 02-google-cloud-oauth-setup.md | Set up the Google Cloud OAuth client and consent screen | 43c6f95 |
| 03 | closed | 03-production-rollout-google-and-rate-limit.md | Production rollout: migrations, env vars, and cross-domain cookie check for Google Sign-In | 58210f7 |
| 04 | closed | 04-student-account-deletion.md | Let a signed-in student delete their own account | 7e63bff |
| 05 | closed | 05-student-question-history.md | Student question history tied to the review loop | be31dc1 |
| 06 | closed | 06-admin-usage-dashboard.md | Admin usage dashboard from rate_limit_hits and question_asks | 4e97c4e |
| 07 | closed | 07-fix-save-and-approve-loses-diff.md | Bug: Save and approve records no correction diff in question_reviews | 92536fb |
| 08 | closed | 08-structured-review-reasons.md | Structured review reasons on reject and edit | a98fc34 |
| 09 | closed | 09-generation-metadata-on-questions.md | Record generation metadata on AI-generated questions | 725bdb8 |
| 10 | closed | 10-prompt-scope-guardrail-and-versioning.md | Answer prompt v2: scope guardrail, uncertainty, curriculum anchoring, versioning | d98cfcc |
| 11 | closed | 11-review-dataset-export.md | Export the human review dataset as JSONL | 0cd840c |
| 12 | closed | 12-ai-review-schema.md | Schema for AI reviews: ai_reviews table and reviewer_kind | 9d4d29b |
| 13 | closed | 13-ai-pre-review-service.md | AI pre-review: rubric prompt and background job for new unreviewed questions | 2aed61f |
| 14 | closed | 14-ai-suggestion-in-review-queue.md | Show the AI pre-review in the admin queue and sort by it | 0ca29f8 |
| 15 | closed | 15-agreement-metrics.md | Measure AI-reviewer agreement with human reviews | 6208a3e |
| 16 | open | 16-few-shot-from-review-history.md | Ground the AI reviewer in similar past human reviews | e106e6c |
| 17 | closed | 17-golden-eval-set-and-ci.md | Golden evaluation set and offline prompt regression check | a3119d1 |
| 18 | open | 18-auto-reject-policy.md | Policy: auto-reject off-topic and unsafe answers with a human audit sample | 70a4933 |
| 19 | open | 19-auto-approve-policy.md | Policy: auto-approve high-confidence answers that closely match approved content | e6ad07e |
| 20 | open | 20-prompt-versioning-and-ab.md | Versioned prompt rollouts with A/B comparison | 274f94c |
| 21 | open | 21-usage-guide-page.md | Add a usage guide page (/help) | ef104ba |
| 22 | closed | 22-robots-allow-privacy.md | robots.txt: allow /privacy (currently Disallow: / blocks the consent-screen check) | 1e98220, e72701a (closed twin) |
| 23 | open | 23-deleted-user-data-disposal.md | Dispose deleted users' residual data (purge rate-limit rows; UUID tombstone for reviewer history) | c08401a |
| 24 | closed | 24-concept-extraction-language-matched-example.md | Concept extraction prompt: language-matched worked example (v3) | bb0fdf8, 73000a3 (closed twin) |
| 25 | closed | 25-ai-review-run-orchestration.md | AI review runs: job records, overlap guard, trigger endpoint, stale re-review | bec062c |
| 26 | open | 26-scheduled-offpeak-ai-review.md | Scheduled AI review runs in DeepSeek's off-peak window | e0594f1 |
| 27 | closed | 27-admin-run-ai-review-all-pending.md | Admin UI: start an AI review run for all pending questions | 0d50e7e |
| 28 | closed | 28-admin-ai-review-selected-questions.md | Admin UI: AI-review selected questions and re-review a single one | c03d036 |
| 29 | closed | 29-prompt-v3-no-diagrams-and-stricter-scope.md | Prompts v3/r2: discourage Mermaid diagrams and tighten the scope criterion | 0becd3b, 84ff079 (closed twin) |
| 30 | open | 30-suspected-errors-in-approved-answers.md | Review: AI reviewer flags possible physics errors in 7 teacher-approved answers | 4ef75f5 |
| 31 | closed | 31-admin-question-id-search-and-label.md | Admin queue: show the question id on each card and allow searching by id | 628e624 |
| 32 | closed | 32-golden-set-lost-relabels-dangling-commit.md | Bug: issue [30]'s golden-set relabels exist only in a dangling commit; branch and tracker disagree | 11ba5fc |
| 33 | closed | 33-align-golden-scope-cases-with-v3-policy.md | Separate the subject and level axes in the v3/r2 prompts; realign the golden scope cases | 20f0a7d |
| 34 | closed | 34-ai-review-run-lifecycle-bugs.md | Bug: AI review run lifecycle: timed-out runs resurrect, skips count as failures, unparsed verdicts never retried | f8db28a |
| 35 | closed | 35-review-response-drops-ai-verdict-ui-defects.md | Bug: review response drops the AI verdict; small admin-UI defects in the AI-review surfaces | f2418a3 |
| 36 | closed | 36-cjk-emphasis-rendering.md | Bug: bold markers around CJK punctuation render literally (CommonMark flanking rules); fix in the renderer, not the data | 1b55272 |
| 37 | open | 37-accept-necessary-advanced-content.md | Accept advanced content the question genuinely needs; the related-QA graph is the scaffolding, not inline derivation | e00868e, b8f3d28 (closed twin) |
| 38 | open | 38-prerequisite-links-not-just-similar.md | Related questions should offer prerequisites, not only similar questions | 1b4f7a1 |
| 39 | open | 39-extract-mathematical-tool-concepts.md | Concept extraction must reliably capture the mathematical tools an answer leans on | 2c422f9 |
| 40 | open | 40-two-axis-difficulty.md | Two-axis difficulty per QA (physics, math), assigned during concept extraction | 785a7e9, bfa263e (closed twin) |
| 41 | open | 41-show-concepts-to-students.md | Show concepts to students as clickable chips; concepts are the map, not admin metadata | 796163b, 0e5e4fa (closed twin) |
| 42 | open | 42-question-page-layout-preview-grid.md | Question-page layout: more related questions, floating preview, and a two-axis grid | 7584a7d, 9cef53e (closed twin) |
| 43 | open | 43-sticky-ask-bar.md | Keep the search/ask box reachable: sticky bar at the bottom of the viewport | be0e1aa, 8e373d4 (closed twin) |
| 44 | open | 44-teacher-reverdict-too-advanced-edits.md | Teacher re-verdict: the old TOO_ADVANCED edits predate the advanced-content policy | fd0b3e9 |
| 45 | open | 45-track-a-student-experience.md | Track A: student experience - the QA graph becomes walkable | 102900d |
| 46 | open | 46-track-b-review-pipeline.md | Track B: review pipeline and policies - resumes after [37] | f87b993 |
| 47 | open | 47-track-c-housekeeping.md | Track C: housekeeping | b904b3d |
| 48 | open | 48-track-d-owner-queue.md | Track D: owner's queue - console, judgement, and go-aheads | 26476f8 |
| 49 | open | 49-similarity-search-in-the-url.md | Put the vector search in the URL (?q=...) and cache query embeddings | 4444d02 |

## Notes on the archive column

- For 22, 24 and 29 the two ids are **two distinct closed issues that
  accidentally shared a number** in the git-bug era; the file covers the
  one whose title it carries, the other lives only in the archive.
- For 37, 40, 41, 42 and 43 the second id is a **merged duplicate** filed
  minutes apart by parallel sessions; its useful points were copied into
  the surviving issue's comments before closing.
- 45-48 are the track queues; 00 is the roadmap epic (its history,
  including the 2026-11-01 replanning comments, is in the archive).
