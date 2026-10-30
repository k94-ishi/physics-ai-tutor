"""Print AI-reviewer agreement with human reviews as text tables."""

import argparse
import sys
from datetime import UTC, date, datetime

from physics_ai_tutor.database.database import SessionLocal
from physics_ai_tutor.schemas.admin_stats import AgreementMetrics
from physics_ai_tutor.services import review_export_service, review_metrics_service


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--since",
        type=date.fromisoformat,
        default=None,
        help="Inclusive start date for the human reviews (default: data cutoff).",
    )
    parser.add_argument(
        "--all", action="store_true", help="Use every review regardless of date."
    )
    return parser.parse_args(argv)


def _pct(value: float | None) -> str:
    return "-" if value is None else f"{value * 100:5.1f}%"


def format_metrics(title: str, metrics: AgreementMetrics) -> str:
    note = "" if metrics.sufficient else "  [n too small]"
    lines = [f"== {title} (n={metrics.n}){note}"]
    lines.append(
        f"exact agreement {_pct(metrics.exact_agreement_rate)}  "
        f"publish agreement {_pct(metrics.publish_agreement_rate)}  "
        f"reject precision {_pct(metrics.reject_precision)}  "
        f"reject recall {_pct(metrics.reject_recall)}  "
        f"reason jaccard {_pct(metrics.reason_jaccard_mean)}"
    )
    lines.append("AI \\ human      APPROVE  EDIT_APPROVE  REJECT")
    for verdict, row in metrics.confusion_matrix.items():
        lines.append(
            f"{verdict:<14} {row['APPROVE']:>8} "
            f"{row['EDIT_APPROVE']:>13} {row['REJECT']:>7}"
        )
    if metrics.calibration:
        lines.append("confidence   n   agreement")
        for bucket in metrics.calibration:
            lines.append(
                f"{bucket.low:.1f}-{bucket.high:.1f}   {bucket.n:>3}   "
                f"{_pct(bucket.agreement_rate)}"
            )
    return "\n".join(lines)


def main(since: date | None = None, include_all: bool = False) -> int:
    if include_all:
        start: datetime | None = None
    elif since is None:
        start = review_export_service.default_since()
    else:
        start = datetime.combine(since, datetime.min.time(), tzinfo=UTC)

    db = SessionLocal()
    try:
        report = review_metrics_service.build_report(db, start)
    finally:
        db.close()

    print(format_metrics("overall", report.overall))
    for label, groups in (
        ("answer prompt", report.by_answer_prompt_version),
        ("reviewer prompt", report.by_reviewer_prompt_version),
        ("month", report.by_month),
    ):
        for name, metrics in groups.items():
            print()
            print(format_metrics(f"{label} {name}", metrics))

    return report.overall.n


if __name__ == "__main__":
    args = parse_args()
    main(args.since, args.all)
    sys.exit(0)
