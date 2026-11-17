"""Comments are English (AGENTS.md coding style, [65]).

Japanese words quoted as data (位相 = phase, `「〜とは」`) are fine; a
comment fails when Japanese makes up a fifth or more of its text.
"""

import io
import re
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JAPANESE = re.compile(r"[぀-ヿ㐀-鿿！-｠]")
QUOTED = re.compile(r"`[^`]*`|\"[^\"]*\"|'[^']*'|「[^」]*」")


def is_japanese_prose(text: str) -> bool:
    letters = re.sub(r"\s", "", QUOTED.sub("", text))
    return bool(letters) and len(JAPANESE.findall(letters)) / len(letters) >= 0.2


def _comments(path: Path) -> list[tuple[int, str]]:
    found = []
    source = path.read_text(encoding="utf-8")
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT:
            found.append((token.start[0], token.string[1:]))
        elif token.type == tokenize.STRING and token.string.startswith(('"""', "'''")):
            # Docstrings and other block strings: judge only obvious prose.
            if token.line.lstrip().startswith(('"""', "'''")):
                found.append((token.start[0], token.string.strip("\"'")))
    return found


def test_no_japanese_comments():
    offenders = [
        f"{path.relative_to(ROOT)}:{line}"
        for folder in ("physics_ai_tutor", "tests", "alembic")
        for path in sorted((ROOT / folder).rglob("*.py"))
        for line, text in _comments(path)
        if is_japanese_prose(text)
    ]
    assert offenders == []


def test_the_rule_tells_prose_from_quoted_data():
    assert is_japanese_prose("概念抽出は質問ごとに並列で実行する")
    assert not is_japanese_prose("位相 is both a wave's phase and topology ([55]).")
    assert not is_japanese_prose('Definition-style wording such as "〜とは" counts.')
