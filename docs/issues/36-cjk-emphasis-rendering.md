---
title: "[36] Bug: bold markers around CJK punctuation render literally (CommonMark flanking rules); fix in the renderer, not the data"
labels: [bug, frontend, markdown]
milestone: M3 AI-assisted review (advisory)
priority: P2
---

**Priority:** P2  **Milestone:** M3 — AI-assisted review (advisory)

## What happened

Text like

```
判断は、**「重心の位置」**と**「支持面（接地している範囲）」**の関係で決まります。
```

renders with only と emphasized and the outer `**` visible as literal
asterisks. Teachers have been fixing these by hand as FORMATTING
edit-approves, but the Markdown is not malformed — the renderer is.

CommonMark's emphasis flanking rules classify a delimiter by its
neighbours, and fullwidth brackets/punctuation (「」（）。、) count as
punctuation: a `**` preceded by `」` and followed by a letter like と is
left-flanking but not right-flanking, so it can only *open* emphasis,
never close it. Japanese has no spaces to rescue the classification, so
`**…」**と**「…**` pairs mismatch. This is the long-known CommonMark CJK
problem (spec issue; the "CJK-friendly" amendment proposal by tats-u
exists precisely for it). Our stack hits it squarely: `MarkdownContent.tsx`
uses react-markdown v10 (micromark, strict CommonMark).

Scale: 21 of 144 `seed.json` entries contain at least one `**` pair that
cannot close under these rules (regex
`\*\*[^*\n]{1,80}?[」）。、！？]\*\*(?=[CJK letter])`), and that is a lower
bound — every new DeepSeek answer can reproduce it, so hand-editing does
not converge.

## What should have happened

The author's intent (`**「重心の位置」**` bold, と plain) renders as such;
no teacher ever edits an answer only to work around the renderer.

## Scope

- Add `remark-cjk-friendly` (the remark plugin of
  micromark-extension-cjk-friendly, which implements the CJK-friendly
  flanking proposal) to the `remarkPlugins` list in
  `frontend/src/components/ui/MarkdownContent.tsx`. This fixes every
  stored answer at render time with no data changes. Verify compatibility
  with react-markdown v10 / unified 11 and with remark-gfm and
  remark-math ordering.
- Fallback if the plugin fights the stack: preprocess the raw string
  before parsing (same place as `normalizeMathDelimiters` in
  `frontend/src/lib/markdown.ts`), e.g. inserting a word joiner or
  rewriting the mismatched pairs — but prefer the plugin, which handles
  all the variants, not just the one regex shape.
- Leave the stored answers and `seed.json` untouched; do not add prompt
  rules telling the model to avoid the pattern (unreliable, bloats the
  prompt, and the data is fine).
- Process note for the review loop: stop recording FORMATTING
  edit-approves whose only change is this pattern — after the fix they
  record a text change that was never needed, which pollutes the review
  dataset and the golden set. Check whether any existing golden EDIT case
  (e.g. p-edit-150 FORMATTING) is actually this renderer artifact and
  relabel if so.

## Acceptance criteria

- [ ] The sample sentence above renders with both bracketed phrases bold
      and no literal asterisks (vitest on MarkdownContent).
- [ ] A seed entry currently affected renders cleanly without its text
      changing.
- [ ] KaTeX, GFM tables, and Mermaid blocks still render (existing tests
      pass).

## Out of scope

- Rewriting stored answers; prompt changes.

## Definition of done

- [ ] Frontend checks pass; regression test added
- [ ] `docs/development.md` notes the plugin and why it exists
