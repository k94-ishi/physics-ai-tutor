from physics_ai_tutor.core import prompts
from physics_ai_tutor.core.prompt_library import load_library
from physics_ai_tutor.services import concept_service

# Captured at import time, before conftest's autouse fixture replaces the
# module attribute with a canned mock for the API tests.
_real_extract_concept_names = concept_service.extract_concept_names

# One entry per prompt family: (version, fingerprint of every text in the
# family). When this test fails, some prompt text changed: bump the family's
# version in core/prompt_library.jsonl and record the new pair here instead
# of editing the old one. (The fingerprint scheme moved from hashing the
# assembled answer prompts to hashing library records on 2026-10-29; the
# answer texts themselves did not change, so its version stayed v2.)
FAMILY_FINGERPRINTS = {
    "ai_review": (
        "r4",
        "e0562f8587db5e89a4f621c2f5a6dd0d182090dd0e8c3fc0376f7c39dfd07829",
    ),
    "answer": (
        "v5",
        "acfb4be41a3201371a48c347ae73ba9648f0a17f6980dcd9e96632922765b57d",
    ),
    "concept_extraction": (
        "v5",
        "315d1e4c2d71078ce1810ae1b09b73db1917d4d02255d3ae79afacc8e8c9b4ae",
    ),
    "translation": (
        "v1",
        "fb1a31598812bb592cbbd6b91ff08e5b2de897f2dae2c28d1bf88c09d73402d4",
    ),
}


def test_every_family_is_pinned():
    assert sorted(FAMILY_FINGERPRINTS) == load_library().families


def test_prompt_versions_match_prompt_texts():
    library = load_library()

    for family, (version, fingerprint) in FAMILY_FINGERPRINTS.items():
        assert library.version(family) == version, (
            f"Prompt family {family!r} is {library.version(family)} but the "
            f"pinned version is {version}; update FAMILY_FINGERPRINTS."
        )
        assert library.fingerprint(family) == fingerprint, (
            f"The {family!r} prompt texts changed but the version did not. "
            "Bump the family's version in core/prompt_library.jsonl and "
            "record the new fingerprint here."
        )


def test_version_constants_come_from_the_library():
    assert prompts.ANSWER_PROMPT_VERSION == "v5"
    assert prompts.TRANSLATION_PROMPT_VERSION == "v1"
    assert concept_service.CONCEPT_EXTRACTION_PROMPT_VERSION == "v5"


def test_concept_extraction_example_matches_the_rows_language(monkeypatch):
    captured = {}

    def _fake(system_prompt, user_prompt):
        captured["user"] = user_prompt
        return "加速度 | acceleration"

    monkeypatch.setattr(
        "physics_ai_tutor.services.deepseek_service.chat_completion", _fake
    )

    _real_extract_concept_names("加速度って何?", "回答", language="ja")
    assert "加速度って何?" in captured["user"]
    assert "What is acceleration?" not in captured["user"]
    assert "written in Japanese" in captured["user"]

    _real_extract_concept_names("What is force?", "An answer.", language="en")
    assert "What is acceleration?" in captured["user"]
    assert "加速度って何?" not in captured["user"].split("---End of example---")[0]
    assert "written in English" in captured["user"]
    # The output format stays bilingual regardless of the example's language.
    assert "加速度 | acceleration" in captured["user"]
