---
title: Answer prompt v2: scope guardrail, uncertainty, curriculum anchoring, versioning
labels: [prompt, security, backend]
milestone: M2 Review data foundation
priority: P1
---

**Priority:** P1  **Milestone:** M2 — Review data foundation

## Summary

Revise `SYSTEM_PROMPTS` so the model stays within high-school physics,
declines other requests briefly, says when it is unsure, and anchors to the
Japanese curriculum; and stop saving or caching declined answers.

## Motivation

Findings from reading `core/prompts.py` and the ask flow:

- Nothing in the prompt limits the topic. Any text 5–200 characters long is
  answered, saved as `UNREVIEWED`, and served from cache to anyone who asks
  the identical string. With self-service login the audience grows; an
  off-topic or inappropriate exchange should never enter the knowledge base.
- No instruction about uncertainty; the model is told to be "正確" but not
  what to do when it cannot be.
- No curriculum anchor (物理基礎 / 物理); "high school" alone lets the model
  reach for university methods, which teachers then reject as
  `TOO_ADVANCED` (#08).
- Japanese prompt: missing "。" after "答えること", a minor but real
  tokenisation wart.
- The English prompt omits "Japanese" curriculum entirely, so EN answers may
  drift from JA ones for the same question.

## Scope

- New prompt text (both languages), `ANSWER_PROMPT_VERSION = "v2"` (#09).
- Scope rule: answer only high-school physics and the mathematics needed for
  it; for anything else reply with one fixed sentence that starts with a
  sentinel the backend can detect (e.g. a leading `[OFF_TOPIC]` token, or a
  short JSON header). Keep the student-facing text friendly.
- `ask_ai`: when the sentinel is present, return the message but **do not**
  call `save_ai_question`, do not translate, and do not count it as a
  generation that others can cache. It still consumes the asker's quota.
- Uncertainty rule: if the question is ambiguous, state the assumption in
  one line before answering; if the model is not confident, say so.
- Curriculum anchor: mention 物理基礎・物理 (high school physics course
  in Japan) and "avoid calculus unless the student uses it first".
- Keep the existing formatting rules ($...$, `\vec{}`, Mermaid, length).

## Acceptance criteria

- [ ] An off-topic prompt (e.g. "英語の宿題を手伝って") yields no new
      `questions` row and a polite one-line reply.
- [ ] The existing physics tests still pass; sample answers reviewed by a
      teacher read as before.
- [ ] `prompt_version` on new rows is `v2`.

## Out of scope

- Content moderation of *inputs* with a separate classifier (revisit if the
  sentinel approach proves leaky; see #18).

## Technical notes

Prefer a sentinel over a second LLM call (AGENTS.md: avoid unnecessary API
calls). Strip the sentinel before returning. Log the event at INFO with the
bucket key so #06 can count it.

## Dependencies

- Blocked by: #09 (version constant; can land in the same PR)
- Blocks: #13 (reviewer rubric reuses the scope definition)

## Definition of done

- [ ] Backend checks pass; prompt change reviewed by a physics teacher
- [ ] `docs/security.md` abuse section mentions the off-topic path
