---
title: "[101] Seed data as one JSONL file; seed.json removed"
labels: [backend, data, docs]
milestone: M1 Student value
priority: P3
---

**Priority:** P3  **Milestone:** M1 — Student value

## Summary

The seed lived in two files: `seed.json` (144 entries with both
languages, provenance, levels and tags, read by the seed) and
`seed.jsonl` (only 21 older entries with `question`/`answer`, used as an
upload example). Make `seed.jsonl` the one complete seed file and delete
`seed.json`.

## Motivation

Owner's request (2026-11-14): JSONL is easier to read and review - one
question per line, so a diff shows only the lines that changed - and two
files with overlapping, diverging content invite mistakes.

## Scope

- `seed.jsonl` holds all 144 entries with every field `seed.json` had,
  same order, one JSON object per line.
- `database/seed_file.py` is the one reader and writer of the format;
  the seed, the `export_seed` CLI and the tests use it.
- `seed.json` deleted; docs (`development.md`, `database.md`,
  `operator-checklist.md`) describe one file.

## Acceptance criteria

- [x] The converted file round-trips: reading `seed.jsonl` gives exactly
      the entries `seed.json` held.
- [x] The offline seed and `export_seed` round-trip tests pass on it.
- [x] Lines of `seed.jsonl` upload through the admin import (texts read,
      other fields ignored), covered by a test.

## Out of scope

- Changing the fields of an entry, or the embeddings file.

## Definition of done

- [x] Backend: `pytest`, `ruff check`, `mypy` pass
- [x] Docs updated

## Log

### 2026-11-14 — done

615 tests pass (614 + 1 new). `seed.json` (504 KB, pretty-printed) is
gone; `seed.jsonl` now carries the full 144 entries. Finding while doing
it: the old `seed.jsonl` was not "the same data in JSONL form", as
`development.md` said - it was the first 21 entries in the legacy
two-field shape, so anyone uploading it as a seed got no translations,
tags or levels. The docs no longer make that claim.
