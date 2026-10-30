"""Typed access to the prompt library (prompt_library.yaml).

Every LLM prompt text lives in the YAML file next to this module, as a list
of records under `prompts`, so wording, language coverage, and versions
are data rather than code. YAML block scalars keep the prose readable with
real line breaks. Python builds the strings it sends from these records;
`tests/test_prompts.py` pins a fingerprint per family so the version must
be bumped whenever any text changes.

Render the library with: uv run python -m physics_ai_tutor.cli.show_prompts
"""

import hashlib
from functools import lru_cache
from importlib import resources

import yaml
from pydantic import BaseModel, field_validator

from physics_ai_tutor.schemas.language import Language

LIBRARY_FILENAME = "prompt_library.yaml"


class PromptRecord(BaseModel):
    family: str
    name: str
    # None for instructions shared by both languages (machine-processing
    # prompts parameterise the language instead; see AGENTS.md).
    language: Language | None = None
    version: str
    description: str = ""
    text: str

    @field_validator("text")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("prompt text must not be empty")
        return value


class PromptLibrary:
    def __init__(self, records: list[PromptRecord]) -> None:
        self._records = records
        self._by_key: dict[tuple[str, str, str | None], PromptRecord] = {}

        for record in records:
            key = (record.family, record.name, record.language)
            if key in self._by_key:
                raise ValueError(f"Duplicate prompt record: {key}")
            self._by_key[key] = record

        for family in {record.family for record in records}:
            versions = {r.version for r in records if r.family == family}
            if len(versions) != 1:
                raise ValueError(
                    f"Prompt family {family!r} mixes versions: {sorted(versions)}"
                )

    def get(
        self, family: str, name: str, language: Language | str | None = None
    ) -> str:
        lang = Language(language) if language is not None else None
        return self._by_key[(family, name, lang)].text

    def version(self, family: str) -> str:
        for record in self._records:
            if record.family == family:
                return record.version
        raise KeyError(family)

    def fingerprint(self, family: str) -> str:
        """Stable hash over a family's texts; pinned in tests per version."""
        parts = [
            f"{r.name}:{r.language or '-'}:{r.text}"
            for r in sorted(
                (r for r in self._records if r.family == family),
                key=lambda r: (r.name, r.language or ""),
            )
        ]
        if not parts:
            raise KeyError(family)
        return hashlib.sha256("\n".join(parts).encode()).hexdigest()

    @property
    def families(self) -> list[str]:
        return sorted({record.family for record in self._records})

    @property
    def records(self) -> list[PromptRecord]:
        return list(self._records)


@lru_cache(maxsize=1)
def load_library() -> PromptLibrary:
    source = resources.files("physics_ai_tutor.core").joinpath(LIBRARY_FILENAME)
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    records = [PromptRecord.model_validate(item) for item in data["prompts"]]
    return PromptLibrary(records)
