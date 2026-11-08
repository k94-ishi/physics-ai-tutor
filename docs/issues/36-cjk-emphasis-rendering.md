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
asterisks. The Markdown is not malformed — the renderer is.

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
- No data repair is needed. Checked 2026-11-01: no review in the
  available history was made only to work around this pattern, and no
  golden case needs relabelling (see "Review-data check" below).

## Acceptance criteria

- [ ] The sample sentence above renders with both bracketed phrases bold
      and no literal asterisks (vitest on MarkdownContent).
- [ ] A seed entry currently affected renders cleanly without its text
      changing.
- [ ] KaTeX, GFM tables, and Mermaid blocks still render (existing tests
      pass).

## Review-data check (2026-11-01)

The worry was that teachers had been hand-fixing this as FORMATTING
edit-approves, which would put phantom "the text needed changing" labels
into the training data. They had not:

- Every FORMATTING case in the golden set has a real, documented reason —
  Mermaid diagram removal (p-edit-17/49/115/150/224/918) or missing `$`
  delimiters (p-edit-721). None is a stray-asterisk fix.
- Of the 18 before/after pairs that can be reconstructed (golden pre-edit
  text vs the current approved text in `seed.json`), **none** differs only
  in emphasis markers.
- In the 4 pairs where the pre-edit text contained the pattern
  (p-edit-49/115/215/1225), it is still present after the teacher's edit —
  it was simply left alone.
- 21 of 144 approved answers in `seed.json` still contain it.

So the dataset is clean and the renderer fix makes those 21 answers
display correctly with no data changes. Limit of the check: the full
production `question_reviews` history was not reachable (the supplied URL
points at the local compose database, which holds no review rows), so
this covers the 57 production cases sampled into the golden set.

## Out of scope

- Rewriting stored answers; prompt changes.

## Definition of done

- [ ] Frontend checks pass; regression test added
- [ ] `docs/development.md` notes the plugin and why it exists
