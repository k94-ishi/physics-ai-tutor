from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from physics_ai_tutor.repositories import stats_repository
from physics_ai_tutor.schemas.admin_stats import AdminStatsResponse, DailyUsage


def fetch_usage_stats(db: Session, days: int) -> AdminStatsResponse:
    today = datetime.now(UTC).date()
    since = datetime.now(UTC) - timedelta(days=days - 1)
    since = since.replace(hour=0, minute=0, second=0, microsecond=0)

    generations = stats_repository.generations_per_day(db, since)
    asks = stats_repository.asks_per_day(db, since)
    unreviewed_count, median_age = stats_repository.unreviewed_backlog(db)

    daily = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        day_asks, day_hits, day_users = asks.get(day, (0, 0, 0))
        daily.append(
            DailyUsage(
                day=day,
                generations=generations.get(day, 0),
                asks=day_asks,
                cache_hits=day_hits,
                distinct_users=day_users,
            )
        )

    return AdminStatsResponse(
        days=days,
        daily=daily,
        unreviewed_count=unreviewed_count,
        unreviewed_median_age_days=median_age,
        anonymous_ip_buckets_24h=stats_repository.anonymous_ip_buckets_since(
            db, timedelta(days=1)
        ),
    )
