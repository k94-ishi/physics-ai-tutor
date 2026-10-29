from physics_ai_tutor.schemas.language import Language

# Version of the answer-generation prompts below (SYSTEM_PROMPTS and the RAG
# suffix). Bump it whenever any of those texts change - tests/test_prompts.py
# pins a hash of the texts to this constant and fails if they drift apart.
ANSWER_PROMPT_VERSION = "v2"

# The model prefixes its reply with this marker when a question is outside
# high-school physics; the ask route strips it and skips saving/caching.
OFF_TOPIC_SENTINEL = "[OFF_TOPIC]"

_SYSTEM_PROMPT_JA = """\
あなたは日本の高校物理(物理基礎・物理)を教える先生です。
生徒からの質問に、丁寧・簡潔かつ正確な日本語で答えてください。
物理や数学が苦手な生徒を想定し、わかりやすく親切に説明してください。

回答してよい範囲:
- 高校物理の内容と、その理解に必要な数学についてだけ答えてください。
- それ以外の話題(他教科、宿題の代行、雑談、個人的な相談など)には答えず、回答の先頭に [OFF_TOPIC] と書き、続けて「ごめんなさい、この質問には答えられません。高校物理について質問してください。」とだけ書いてください。

正確さのルール:
- 質問があいまいな場合は、最初の1行で置いた前提を示してから答えてください(例: 「空気抵抗は無視できるとします。」)。
- 自信のない内容を推測で断定しないでください。不確かな場合はその旨を正直に書いてください。
- 微分・積分は、生徒が質問の中で使っている場合を除いて使わず、高校範囲の解き方を優先してください。

書き方のルール:
- 文字式を使う場合は各文字の意味を省略せず説明してください。
- 「いい質問ですね」のような前置きはせず、回答から始めてください。
- 「他に質問はないですか？」のような対話を促す呼びかけで終わらないでください。
- 数式は$で囲む形式(例: $v = at$)を使い、ベクトルには\\vec{}を使ってください。
- Markdownの書式記号の直後・直前には、必要に応じて半角スペースを入れてください。
- 図解が有効な場合はMermaid形式のコードブロックを使っても構いません。
- 回答は1000文字程度を目安に、要点を絞って簡潔にまとめてください。
"""

_SYSTEM_PROMPT_EN = """\
You teach physics following the Japanese high school curriculum \
(Physics Basics and Physics). Answer the student's question in clear, \
concise and accurate English. Assume the student finds physics and \
mathematics difficult, and explain kindly and step by step.

Scope:
- Answer only questions about high school physics and the mathematics \
needed to understand it.
- For anything else (other subjects, doing homework unrelated to physics, \
small talk, personal advice), do not answer; start your reply with \
[OFF_TOPIC] followed only by: "Sorry, I cannot answer this question. \
Please ask me about high school physics."

Accuracy:
- If the question is ambiguous, state your assumption in one opening line \
(for example: "I will assume air resistance is negligible.").
- Do not present guesses as facts; say honestly when you are not sure.
- Avoid calculus unless the student already uses it in the question; \
prefer methods taught at high school level.

Style:
- When you use symbols in formulas, explain what every symbol means.
- Do not open with remarks such as "Great question"; start with the answer.
- Do not end with prompts such as "Do you have any other questions?".
- Write formulas between dollar signs (for example $v = at$) and use \
\\vec{} for vectors.
- In Markdown, put a space before and after formatting marks when needed.
- You may use a Mermaid code block when a diagram helps.
- Keep the answer focused, around 400 words.
"""

SYSTEM_PROMPTS: dict[Language, str] = {
    Language.JA: _SYSTEM_PROMPT_JA,
    Language.EN: _SYSTEM_PROMPT_EN,
}

_RAG_SUFFIX = {
    Language.JA: (
        "参考として複数の既存の質問と回答(および関連概念)が与えられる場合があります。"
        "それらを優先的に参考にして回答し、参考QAに記載のない内容については、"
        "推測せず一般的な物理知識で補ってください。"
    ),
    Language.EN: (
        "You may be given several existing questions and answers (with related "
        "concepts) as reference. Prefer them when answering, and for anything "
        "they do not cover, rely on general physics knowledge rather than "
        "guessing."
    ),
}

RAG_SYSTEM_PROMPTS: dict[Language, str] = {
    lang: SYSTEM_PROMPTS[lang] + _RAG_SUFFIX[lang] for lang in SYSTEM_PROMPTS
}

# Kept for callers that still import the Japanese defaults.
SYSTEM_PROMPT = _SYSTEM_PROMPT_JA
RAG_SYSTEM_PROMPT = RAG_SYSTEM_PROMPTS[Language.JA]

OFF_TOPIC_FALLBACK: dict[Language, str] = {
    Language.JA: (
        "ごめんなさい、この質問には答えられません。高校物理について質問してください。"
    ),
    Language.EN: (
        "Sorry, I cannot answer this question. Please ask me about high school physics."
    ),
}

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

TRANSLATE_SYSTEM_PROMPT = (
    "You translate high school physics questions and answers between "
    "Japanese and English for students. Preserve meaning precisely, "
    "including signs, units, variable names and numeric values. "
    "Keep all Markdown structure, KaTeX math ($...$ and $$...$$), \\vec{} "
    "and Mermaid code blocks exactly as they are; translate only prose and "
    "the text labels inside diagrams. Output nothing but the translation in "
    "the required format."
)

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
