from physics_ai_tutor.core.prompt_library import load_library
from physics_ai_tutor.schemas.language import Language

_LIBRARY = load_library()

# Versions come from the prompt library (prompt_library.yaml). Bump a
# family's version there whenever any of its texts change -
# tests/test_prompts.py pins a fingerprint per family and fails on drift.
ANSWER_PROMPT_VERSION = _LIBRARY.version("answer")
TRANSLATION_PROMPT_VERSION = _LIBRARY.version("translation")

# The model prefixes its reply with this marker when a question is outside
# high-school physics; the ask route strips it and skips saving/caching.
OFF_TOPIC_SENTINEL = "[OFF_TOPIC]"

SYSTEM_PROMPTS: dict[Language, str] = {
    lang: _LIBRARY.get("answer", "system", lang) for lang in Language
}

_RAG_SUFFIX: dict[Language, str] = {
    lang: _LIBRARY.get("answer", "rag_suffix", lang) for lang in Language
}

RAG_SYSTEM_PROMPTS: dict[Language, str] = {
    lang: SYSTEM_PROMPTS[lang] + _RAG_SUFFIX[lang] for lang in SYSTEM_PROMPTS
}

# Kept for callers that still import the Japanese defaults.
SYSTEM_PROMPT = SYSTEM_PROMPTS[Language.JA]
RAG_SYSTEM_PROMPT = RAG_SYSTEM_PROMPTS[Language.JA]

OFF_TOPIC_FALLBACK: dict[Language, str] = {
    lang: _LIBRARY.get("answer", "off_topic_fallback", lang) for lang in Language
}

TRANSLATE_SYSTEM_PROMPT = _LIBRARY.get("translation", "system")
TRANSLATE_USER_TEMPLATE = _LIBRARY.get("translation", "user_template")

RAG_CONTEXT_LABELS: dict[Language, dict[str, str]] = {
    Language.JA: {
        "block": "参考QA{index}",
        "question": "質問",
        "answer": "回答",
        "concepts": "関連概念",
        "none": "なし",
        "instruction": (
            "上記は参考になる可能性のある既存の質問と回答です。"
            "これらを踏まえて、以下の生徒の質問に答えてください。"
        ),
    },
    Language.EN: {
        "block": "Reference QA {index}",
        "question": "Question",
        "answer": "Answer",
        "concepts": "Related concepts",
        "none": "none",
        "instruction": (
            "The above are existing questions and answers that may be relevant. "
            "Taking them into account, answer the student's question below."
        ),
    },
}

LANGUAGE_NAMES: dict[Language, str] = {
    Language.JA: "Japanese",
    Language.EN: "English",
}

# Preferred English renderings of Japanese physics terms, used by the
# translation and concept extraction prompts so generated text matches the
# vocabulary of the hand-translated content.
GLOSSARY: dict[str, str] = {
    "速さ": "speed",
    "速度": "velocity",
    "加速度": "acceleration",
    "等速直線運動": "uniform linear motion",
    "等加速度直線運動": "uniformly accelerated linear motion",
    "自由落下": "free fall",
    "鉛直投げ上げ": "vertical upward throw",
    "変位": "displacement",
    "移動距離": "distance travelled",
    "位置": "position",
    "基準点": "reference point",
    "単位時間": "unit time",
    "瞬間の速さ": "instantaneous speed",
    "平均の速さ": "average speed",
    "重力": "gravity",
    "重力加速度": "gravitational acceleration",
    "空気抵抗": "air resistance",
    "摩擦": "friction",
    "質量": "mass",
    "力": "force",
    "ベクトル": "vector",
    "スカラー": "scalar",
    "最高点": "highest point",
    "位置-時間グラフ": "position-time graph",
    "速度-時間グラフ": "velocity-time graph",
    "x-tグラフ": "x-t graph",
    "v-tグラフ": "v-t graph",
    "傾き": "slope",
    "接線": "tangent line",
    "慣性": "inertia",
    "作用・反作用": "action and reaction",
    "運動方程式": "equation of motion",
    "運動量": "momentum",
    "運動エネルギー": "kinetic energy",
    "位置エネルギー": "potential energy",
    "力学的エネルギー": "mechanical energy",
    "仕事": "work",
    "仕事率": "power",
    "周期": "period",
    "振動数": "frequency",
    "波長": "wavelength",
    "振幅": "amplitude",
}

TRANSLATE_USER_TEMPLATE = """\
Translate the following physics Q&A from {source} to {target}.
{glossary}
Return exactly this format, with the two marker lines unchanged:

=====QUESTION=====
<translated question>
=====ANSWER=====
<translated answer>

=====QUESTION=====
{question}
=====ANSWER=====
{answer}
"""


def glossary_block() -> str:
    if not GLOSSARY:
        return ""

    lines = "\n".join(f"- {ja}: {en}" for ja, en in GLOSSARY.items())
    return f"Use these term translations:\n{lines}\n"
