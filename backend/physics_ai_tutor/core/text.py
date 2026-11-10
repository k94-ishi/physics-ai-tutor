"""Text normalisation rules shared by search, caching and concept matching."""

import unicodedata


def normalize_text(text: str) -> str:
    """NFKC with whitespace collapsed; keeps case (query cache key)."""
    return " ".join(unicodedata.normalize("NFKC", text).split())


def normalize_key(text: str) -> str:
    """normalize_text plus case folding (concept term matching key)."""
    return normalize_text(text).casefold()


def concept_pair_text(ja: str | None, en: str | None) -> str:
    """The text a concept's embedding is computed from; seed vectors key on it."""
    return " | ".join(part for part in (ja, en) if part)


def concept_line(ja: str | None, en: str | None) -> str:
    """A concept in the extraction format `<ja> | <en>` (either side may be empty)."""
    return f"{ja or ''} | {en or ''}"
