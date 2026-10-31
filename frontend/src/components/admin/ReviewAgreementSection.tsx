"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchReviewAgreement } from "@/lib/api";
import { AgreementMetrics, ReviewAgreementResponse } from "@/types/question";
import Card from "@/components/ui/Card";
import LoadingState from "@/components/ui/LoadingState";
import StatusMessage from "@/components/ui/StatusMessage";
import { useLanguage } from "@/lib/i18n/LanguageContext";

const AI_VERDICTS = ["APPROVE", "EDIT", "REJECT", "UNPARSED"] as const;
const HUMAN_ACTIONS = ["APPROVE", "EDIT_APPROVE", "REJECT"] as const;

// Which human action counts as exact agreement with each AI verdict.
const MATCHING_ACTION: Record<string, string> = {
    APPROVE: "APPROVE",
    EDIT: "EDIT_APPROVE",
    REJECT: "REJECT",
};

function pct(value: number | null): string {
    return value === null ? "—" : `${Math.round(value * 100)}%`;
}

function Metric({ label, value }: { label: string; value: string }) {
    return (
        <div className="flex flex-col gap-0.5">
            <span className="text-xs text-gray-500">{label}</span>
            <span className="text-lg font-semibold text-gray-900">{value}</span>
        </div>
    );
}

function MetricsBlock({
    title,
    metrics,
}: {
    title: string;
    metrics: AgreementMetrics;
}) {
    const { t } = useLanguage();

    return (
        <Card className="flex flex-col gap-4">
            <div className="flex items-center justify-between gap-3">
                <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
                {!metrics.sufficient && (
                    <span className="rounded-full bg-yellow-50 px-2 py-0.5 text-xs font-medium text-yellow-800">
                        {t("adminStats.agreementTooSmall", { n: metrics.n })}
                    </span>
                )}
            </div>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                <Metric label={t("adminStats.agreementPairs")} value={String(metrics.n)} />
                <Metric
                    label={t("adminStats.exactAgreement")}
                    value={pct(metrics.exact_agreement_rate)}
                />
                <Metric
                    label={t("adminStats.publishAgreement")}
                    value={pct(metrics.publish_agreement_rate)}
                />
                <Metric
                    label={t("adminStats.rejectPrecision")}
                    value={pct(metrics.reject_precision)}
                />
                <Metric
                    label={t("adminStats.rejectRecall")}
                    value={pct(metrics.reject_recall)}
                />
                <Metric
                    label={t("adminStats.reasonJaccard")}
                    value={pct(metrics.reason_jaccard_mean)}
                />
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <div className="overflow-x-auto">
                    <p className="mb-1 text-xs font-medium text-gray-500">
                        {t("adminStats.matrixHeading")}
                    </p>
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-gray-200 text-left text-gray-500">
                                <th className="py-1 pr-3 font-medium">
                                    {t("adminStats.matrixAi")}
                                </th>
                                {HUMAN_ACTIONS.map((action) => (
                                    <th key={action} className="py-1 pr-3 font-medium">
                                        {action}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {AI_VERDICTS.map((verdict) => (
                                <tr key={verdict} className="border-b border-gray-100">
                                    <td className="py-1 pr-3 text-gray-700">
                                        {verdict === "UNPARSED"
                                            ? t("adminStats.aiUnparsed")
                                            : verdict}
                                    </td>
                                    {HUMAN_ACTIONS.map((action) => (
                                        <td
                                            key={action}
                                            className={`py-1 pr-3 ${
                                                MATCHING_ACTION[verdict] === action
                                                    ? "font-semibold text-green-700"
                                                    : "text-gray-900"
                                            }`}
                                        >
                                            {metrics.confusion_matrix[verdict]?.[action] ?? 0}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                <div className="overflow-x-auto">
                    <p className="mb-1 text-xs font-medium text-gray-500">
                        {t("adminStats.calibrationHeading")}
                    </p>
                    {metrics.calibration.length === 0 ? (
                        <p className="text-sm text-gray-500">—</p>
                    ) : (
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-gray-200 text-left text-gray-500">
                                    <th className="py-1 pr-3 font-medium">
                                        {t("adminStats.calibrationConfidence")}
                                    </th>
                                    <th className="py-1 pr-3 font-medium">
                                        {t("adminStats.calibrationCount")}
                                    </th>
                                    <th className="py-1 font-medium">
                                        {t("adminStats.calibrationRate")}
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                {metrics.calibration.map((bucket) => (
                                    <tr key={bucket.low} className="border-b border-gray-100">
                                        <td className="py-1 pr-3 text-gray-700">
                                            {bucket.low.toFixed(1)}–{bucket.high.toFixed(1)}
                                        </td>
                                        <td className="py-1 pr-3 text-gray-900">{bucket.n}</td>
                                        <td className="py-1 text-gray-900">
                                            {pct(bucket.agreement_rate)}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>
        </Card>
    );
}

function Groups({
    heading,
    groups,
}: {
    heading: string;
    groups: Record<string, AgreementMetrics>;
}) {
    const names = Object.keys(groups);
    // A single group repeats the overall block; show groups only when they split.
    if (names.length <= 1) {
        return null;
    }

    return (
        <section className="flex flex-col gap-3">
            <h3 className="text-sm font-semibold text-gray-700">{heading}</h3>
            {names.map((name) => (
                <MetricsBlock key={name} title={name} metrics={groups[name]} />
            ))}
        </section>
    );
}

/** Agreement between the AI pre-reviewer and the teachers who reviewed later. */
export default function ReviewAgreementSection() {
    const { t } = useLanguage();
    const [report, setReport] = useState<ReviewAgreementResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    const load = useCallback(async () => {
        setLoading(true);
        setError(false);

        try {
            setReport(await fetchReviewAgreement());
        } catch (err) {
            console.error(err);
            setError(true);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        load();
    }, [load]);

    return (
        <section className="flex flex-col gap-4">
            <div>
                <h2 className="text-lg font-semibold text-gray-900">
                    {t("adminStats.agreementTitle")}
                </h2>
                <p className="text-xs text-gray-500">{t("adminStats.agreementHint")}</p>
            </div>

            {loading && <LoadingState />}

            {!loading && (error || report === null) && (
                <StatusMessage
                    variant="error"
                    message={t("adminStats.agreementFetchFailed")}
                    onRetry={load}
                />
            )}

            {!loading && report !== null && !error && (
                <>
                    <MetricsBlock
                        title={t("adminStats.agreementPairs")}
                        metrics={report.overall}
                    />
                    <Groups
                        heading={t("adminStats.groupReviewerPrompt")}
                        groups={report.by_reviewer_prompt_version}
                    />
                    <Groups
                        heading={t("adminStats.groupAnswerPrompt")}
                        groups={report.by_answer_prompt_version}
                    />
                    <Groups heading={t("adminStats.groupMonth")} groups={report.by_month} />
                </>
            )}
        </section>
    );
}
