from datetime import date, datetime

from pydantic import BaseModel


class DailyUsage(BaseModel):
    day: date
    # Questions created by the AI pipeline (any caller, cache misses only).
    generations: int
    # Signed-in asks, cache hits included; anonymous asks are not recorded.
    asks: int
    # Signed-in asks answered from the cache (no LLM call).
    cache_hits: int
    distinct_users: int


class AdminStatsResponse(BaseModel):
    days: int
    daily: list[DailyUsage]
    unreviewed_count: int
    unreviewed_median_age_days: float | None
    # Distinct anonymous IP buckets that triggered a generation in the last
    # 24 hours; rate_limit_hits is pruned daily, so no longer window exists.
    anonymous_ip_buckets_24h: int


class CalibrationBucket(BaseModel):
    """AI confidence decile -> how often the human agreed exactly."""

    low: float
    high: float
    n: int
    agreement_rate: float | None


class AgreementMetrics(BaseModel):
    n: int
    # False below the minimum sample; the rates are then shown as unreliable.
    sufficient: bool
    # AI verdict matched the human action one-to-one
    # (APPROVE/APPROVE, EDIT/EDIT_APPROVE, REJECT/REJECT).
    exact_agreement_rate: float | None
    # Both sides agreed on whether the answer should be published at all.
    publish_agreement_rate: float | None
    # AI REJECT as a predictor of human REJECT.
    reject_precision: float | None
    reject_recall: float | None
    # Mean Jaccard overlap of reason codes where both sides gave reasons.
    reason_jaccard_mean: float | None
    # ai_verdict -> human_action -> count ("UNPARSED" for verdict-less rows).
    confusion_matrix: dict[str, dict[str, int]]
    calibration: list[CalibrationBucket]


class ReviewAgreementResponse(BaseModel):
    since: datetime | None
    overall: AgreementMetrics
    by_answer_prompt_version: dict[str, AgreementMetrics]
    by_reviewer_prompt_version: dict[str, AgreementMetrics]
    by_month: dict[str, AgreementMetrics]
