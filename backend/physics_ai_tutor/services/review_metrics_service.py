from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import datetime

from sqlalchemy.orm import Session

from physics_ai_tutor.repositories import review_metrics_repository
from physics_ai_tutor.repositories.review_metrics_repository import ReviewPair
from physics_ai_tutor.schemas.admin_stats import (
    AgreementMetrics,
    CalibrationBucket,
    ReviewAgreementResponse,
)

# Below this many pairs the rates are noise; the UI says so instead.
MIN_PAIRS = 30

AI_VERDICTS = ("APPROVE", "EDIT", "REJECT", "UNPARSED")
HUMAN_ACTIONS = ("APPROVE", "EDIT_APPROVE", "REJECT")

# The human action that counts as exact agreement with each AI verdict.
MATCHING_ACTION = {"APPROVE": "APPROVE", "EDIT": "EDIT_APPROVE", "REJECT": "REJECT"}

PUBLISH_VERDICTS = {"APPROVE", "EDIT"}
PUBLISH_ACTIONS = {"APPROVE", "EDIT_APPROVE"}


def _verdict_label(pair: ReviewPair) -> str:
    return pair.ai_verdict or "UNPARSED"


def _agrees_exactly(pair: ReviewPair) -> bool:
    return MATCHING_ACTION.get(pair.ai_verdict or "") == pair.human_action


def _agrees_on_publishing(pair: ReviewPair) -> bool:
    # An unparsed verdict is no verdict: it cannot agree with anything.
    if pair.ai_verdict is None:
        return False

    return (pair.ai_verdict in PUBLISH_VERDICTS) == (
        pair.human_action in PUBLISH_ACTIONS
    )


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _reason_jaccard(pair: ReviewPair) -> float | None:
    """Overlap between the human's reason and the AI's reasons (both present)."""
    if pair.human_reason is None or not pair.ai_reasons:
        return None

    human = {pair.human_reason}
    ai = set(pair.ai_reasons)

    return len(human & ai) / len(human | ai)


def _calibration(pairs: list[ReviewPair]) -> list[CalibrationBucket]:
    buckets: dict[int, list[ReviewPair]] = defaultdict(list)

    for pair in pairs:
        if pair.ai_confidence is None:
            continue
        # 1.0 lands in the top decile rather than an eleventh bucket.
        decile = min(int(pair.ai_confidence * 10), 9)
        buckets[decile].append(pair)

    return [
        CalibrationBucket(
            low=decile / 10,
            high=(decile + 1) / 10,
            n=len(members),
            agreement_rate=_rate(
                sum(_agrees_exactly(p) for p in members), len(members)
            ),
        )
        for decile, members in sorted(buckets.items())
    ]


def compute_agreement(pairs: list[ReviewPair]) -> AgreementMetrics:
    n = len(pairs)
    matrix = {
        verdict: {action: 0 for action in HUMAN_ACTIONS} for verdict in AI_VERDICTS
    }
    for pair in pairs:
        matrix[_verdict_label(pair)][pair.human_action] += 1

    ai_reject = [p for p in pairs if p.ai_verdict == "REJECT"]
    human_reject = [p for p in pairs if p.human_action == "REJECT"]
    true_reject = [p for p in ai_reject if p.human_action == "REJECT"]

    jaccards = [j for j in (_reason_jaccard(p) for p in pairs) if j is not None]

    return AgreementMetrics(
        n=n,
        sufficient=n >= MIN_PAIRS,
        exact_agreement_rate=_rate(sum(_agrees_exactly(p) for p in pairs), n),
        publish_agreement_rate=_rate(sum(_agrees_on_publishing(p) for p in pairs), n),
        reject_precision=_rate(len(true_reject), len(ai_reject)),
        reject_recall=_rate(len(true_reject), len(human_reject)),
        reason_jaccard_mean=sum(jaccards) / len(jaccards) if jaccards else None,
        confusion_matrix=matrix,
        calibration=_calibration(pairs),
    )


def _grouped(
    pairs: Iterable[ReviewPair], key: Callable[[ReviewPair], str]
) -> dict[str, AgreementMetrics]:
    groups: dict[str, list[ReviewPair]] = defaultdict(list)
    for pair in pairs:
        groups[key(pair)].append(pair)

    return {
        name: compute_agreement(members) for name, members in sorted(groups.items())
    }


def build_report(db: Session, since: datetime | None) -> ReviewAgreementResponse:
    pairs = review_metrics_repository.list_pairs(db, since)

    return ReviewAgreementResponse(
        since=since,
        overall=compute_agreement(pairs),
        by_answer_prompt_version=_grouped(
            pairs, lambda p: p.answer_prompt_version or "unknown"
        ),
        by_reviewer_prompt_version=_grouped(pairs, lambda p: p.reviewer_prompt_version),
        by_month=_grouped(pairs, lambda p: p.reviewed_at.strftime("%Y-%m")),
    )
