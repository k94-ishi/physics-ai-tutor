import hashlib

from physics_ai_tutor.core import prompts


def _answer_prompt_hash() -> str:
    """One hash over every text that shapes an answer generation."""
    texts = [prompts.SYSTEM_PROMPTS[lang] for lang in sorted(prompts.SYSTEM_PROMPTS)]
    texts += [
        prompts.RAG_SYSTEM_PROMPTS[lang] for lang in sorted(prompts.RAG_SYSTEM_PROMPTS)
    ]

    return hashlib.sha256("\n".join(texts).encode()).hexdigest()


# One entry per released prompt version. When this test fails, the prompt
# text changed: bump prompts.ANSWER_PROMPT_VERSION and add the new pair here
# instead of editing the old one.
VERSION_HASHES = {
    "v1": "1e0b352610e376de185c7b5e58aa4a414c2ce211e60b8463b14c4b06e1b5afee",
    "v2": "bf43a65b1c5b2ffa6903531b5814bbcab417bc462c000b0d798e8d792a059aac",
}


def test_answer_prompt_version_matches_prompt_text():
    assert prompts.ANSWER_PROMPT_VERSION in VERSION_HASHES, (
        "Unknown ANSWER_PROMPT_VERSION; add it to VERSION_HASHES."
    )
    assert VERSION_HASHES[prompts.ANSWER_PROMPT_VERSION] == _answer_prompt_hash(), (
        "The answer prompts changed but ANSWER_PROMPT_VERSION did not. "
        "Bump the version in core/prompts.py and record the new hash here."
    )
