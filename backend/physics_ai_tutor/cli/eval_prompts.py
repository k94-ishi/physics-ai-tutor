"""Offline prompt regression check against the golden evaluation set.

Grades each golden Q&A with the current reviewer prompt (optionally
regenerating the answers with the current answer prompt first), computes
the agreement metrics against the hand labels, and compares them with the
committed baseline for the same prompt versions. Needs only the DeepSeek
key - no database. Eval calls pin temperature=0 for reproducibility.
"""

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from physics_ai_tutor.cli.review_metrics import format_metrics
from physics_ai_tutor.core import prompts
from physics_ai_tutor.repositories.review_metrics_repository import ReviewPair
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.question_review import QuestionReviewReason
from physics_ai_tutor.services import ai_review_service, deepseek_service
from physics_ai_tutor.services.review_metrics_service import compute_agreement

EVAL_DIR = Path(__file__).resolve().parents[2] / "eval"
DEFAULT_SET = EVAL_DIR / "golden.jsonl"
EVAL_TEMPERATURE = 0.0
DEFAULT_TOLERANCE = 0.05

# Expected verdict -> the human action it stands for in the metrics.
ACTION_FOR_VERDICT = {"APPROVE": "APPROVE", "EDIT": "EDIT_APPROVE", "REJECT": "REJECT"}


class GoldenCase(BaseModel):
    id: str
    language: Language
    question: str
    answer: str
    expected_verdict: str = Field(pattern="^(APPROVE|EDIT|REJECT)$")
    expected_reasons: list[QuestionReviewReason] = Field(default_factory=list)
    note: str = ""


def load_golden_set(path: Path) -> list[GoldenCase]:
    cases = [
        GoldenCase.model_validate(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    ids = [case.id for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate case ids in the golden set")
    if not cases:
        raise ValueError("The golden set is empty")

    return cases


def set_fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def baseline_path() -> Path:
    return EVAL_DIR / (
        f"baseline-{prompts.ANSWER_PROMPT_VERSION}"
        f"-{ai_review_service.REVIEW_PROMPT_VERSION}.json"
    )


def grade_cases(
    cases: list[GoldenCase], regenerate: bool, verbose: bool = False
) -> list[ReviewPair]:
    """One ReviewPair per case; the hand label plays the human reviewer."""
    now = datetime.now(UTC)
    pairs = []

    for index, case in enumerate(cases):
        answer = case.answer
        if regenerate:
            answer = deepseek_service.generate_answer(
                prompts.SYSTEM_PROMPTS[case.language],
                case.question,
                temperature=EVAL_TEMPERATURE,
            ).content

        graded = ai_review_service.grade_answer(
            case.question, answer, case.language, temperature=EVAL_TEMPERATURE
        )
        verdict = graded.verdict.value if graded.verdict else None
        expected = ACTION_FOR_VERDICT[case.expected_verdict]

        marker = "ok " if ACTION_FOR_VERDICT.get(verdict or "") == expected else "DIFF"
        print(
            f"  [{marker}] {case.id} expected={case.expected_verdict:<7} "
            f"got={verdict or 'UNPARSED':<8} "
            f"reasons={','.join(r.value for r in graded.reasons) or '-'}"
        )
        if verbose and marker == "DIFF" and graded.rationale:
            # The rationale is what a teacher needs to judge who is right.
            print(f"         why: {graded.rationale[:400]}")

        pairs.append(
            ReviewPair(
                question_id=index,
                human_action=expected,
                human_reason=(
                    case.expected_reasons[0].value if case.expected_reasons else None
                ),
                ai_verdict=verdict,
                ai_confidence=graded.confidence,
                ai_reasons=tuple(r.value for r in graded.reasons),
                answer_prompt_version=prompts.ANSWER_PROMPT_VERSION,
                reviewer_prompt_version=ai_review_service.REVIEW_PROMPT_VERSION,
                reviewed_at=now,
            )
        )

    return pairs


def summarize(cases: list[GoldenCase]) -> str:
    verdicts: dict[str, int] = {}
    languages: dict[str, int] = {}
    for case in cases:
        verdicts[case.expected_verdict] = verdicts.get(case.expected_verdict, 0) + 1
        languages[case.language.value] = languages.get(case.language.value, 0) + 1

    return (
        f"{len(cases)} cases | verdicts {dict(sorted(verdicts.items()))} | "
        f"languages {dict(sorted(languages.items()))}"
    )


def compare_with_baseline(metrics, set_hash: str, tolerance: float) -> int:
    """0 = pass, 1 = regression, 0 with a warning when no baseline exists."""
    path = baseline_path()
    if not path.exists():
        print(
            f"NO BASELINE at {path.name}; eyeball the numbers above "
            "and run --save-baseline to pin them."
        )
        return 0

    baseline = json.loads(path.read_text(encoding="utf-8"))
    if baseline.get("set_sha256") != set_hash:
        print(
            "WARNING: the golden set changed since the baseline was saved; "
            "comparison may not be meaningful."
        )

    failures = []
    for key in ("exact_agreement_rate", "reject_precision"):
        before = baseline.get(key)
        after = getattr(metrics, key)
        if before is not None and (after is None or after < before - tolerance):
            shown = "None" if after is None else f"{after:.3f}"
            failures.append(f"{key}: {before:.3f} -> {shown}")

    if failures:
        print("FAIL vs baseline " + path.name + ": " + "; ".join(failures))
        return 1

    print(f"PASS vs baseline {path.name} (tolerance {tolerance})")
    return 0


def save_baseline(metrics, set_hash: str) -> Path:
    path = baseline_path()
    path.write_text(
        json.dumps(
            {
                "answer_prompt_version": prompts.ANSWER_PROMPT_VERSION,
                "reviewer_prompt_version": ai_review_service.REVIEW_PROMPT_VERSION,
                "set_sha256": set_hash,
                "n": metrics.n,
                "exact_agreement_rate": metrics.exact_agreement_rate,
                "publish_agreement_rate": metrics.publish_agreement_rate,
                "reject_precision": metrics.reject_precision,
                "reject_recall": metrics.reject_recall,
                "created_at": datetime.now(UTC).isoformat(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", type=Path, default=DEFAULT_SET)
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerate the answers with the current answer prompt first "
        "(doubles the API calls).",
    )
    parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="Write the run's metrics as the baseline for these prompt versions.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the set and baseline without any API call.",
    )
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)
    parser.add_argument(
        "--verbose", action="store_true", help="Print the AI rationale on DIFF lines."
    )
    return parser.parse_args()


def main(
    set_path: Path = DEFAULT_SET,
    regenerate: bool = False,
    save: bool = False,
    dry_run: bool = False,
    tolerance: float = DEFAULT_TOLERANCE,
    verbose: bool = False,
) -> int:
    cases = load_golden_set(set_path)
    set_hash = set_fingerprint(set_path)
    print(f"golden set: {summarize(cases)}")
    print(
        f"prompts: answer={prompts.ANSWER_PROMPT_VERSION} "
        f"reviewer={ai_review_service.REVIEW_PROMPT_VERSION}"
    )

    if dry_run:
        exists = baseline_path().exists()
        print(f"baseline {baseline_path().name}: {'present' if exists else 'missing'}")
        print("dry run: set is valid; no API calls made.")
        return 0

    pairs = grade_cases(cases, regenerate, verbose)
    metrics = compute_agreement(pairs)
    print()
    print(format_metrics("golden set", metrics))
    print()

    if save:
        path = save_baseline(metrics, set_hash)
        print(f"baseline written: {path.name}")
        return 0

    return compare_with_baseline(metrics, set_hash, tolerance)


if __name__ == "__main__":
    args = parse_args()
    sys.exit(
        main(
            args.set,
            args.regenerate,
            args.save_baseline,
            args.dry_run,
            args.tolerance,
            args.verbose,
        )
    )
