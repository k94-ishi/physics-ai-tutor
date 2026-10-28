from datetime import date

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
