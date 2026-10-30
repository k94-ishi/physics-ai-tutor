"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchAdminStats } from "@/lib/api";
import { AdminStatsResponse } from "@/types/question";
import Card from "@/components/ui/Card";
import LoadingState from "@/components/ui/LoadingState";
import StatusMessage from "@/components/ui/StatusMessage";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import ReviewAgreementSection from "@/components/admin/ReviewAgreementSection";

const DAY_OPTIONS = [7, 14, 30, 90];

function Metric({ label, value }: { label: string; value: string }) {
    return (
        <Card className="flex flex-col gap-1">
            <span className="text-xs text-gray-500">{label}</span>
            <span className="text-xl font-semibold text-gray-900">{value}</span>
        </Card>
    );
}

export default function AdminStatsPage() {
    const { language, t } = useLanguage();
    const [stats, setStats] = useState<AdminStatsResponse | null>(null);
    const [days, setDays] = useState(14);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    const load = useCallback(async () => {
        setLoading(true);
        setError(false);

        try {
            setStats(await fetchAdminStats(days));
        } catch (error) {
            console.error(error);
            setError(true);
        } finally {
            setLoading(false);
        }
    }, [days]);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        load();
    }, [load]);

    if (loading) {
        return <LoadingState />;
    }

    if (error || stats === null) {
        return (
            <StatusMessage
                variant="error"
                message={t("adminStats.fetchFailed")}
                onRetry={load}
            />
        );
    }

    const locale = language === "ja" ? "ja-JP" : "en-US";

    return (
        <main className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-gray-900">
                    {t("adminStats.title")}
                </h1>

                <label className="flex items-center gap-2 text-sm text-gray-600">
                    {t("adminStats.daysLabel")}
                    <select
                        value={days}
                        onChange={(e) => setDays(Number(e.target.value))}
                        className="rounded-md border border-gray-300 bg-white px-2 py-1 text-sm"
                    >
                        {DAY_OPTIONS.map((option) => (
                            <option key={option} value={option}>
                                {t("adminStats.daysUnit", { count: option })}
                            </option>
                        ))}
                    </select>
                </label>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <Metric
                    label={t("adminStats.unreviewedCount")}
                    value={String(stats.unreviewed_count)}
                />
                <Metric
                    label={t("adminStats.unreviewedMedianAge")}
                    value={
                        stats.unreviewed_median_age_days === null
                            ? "—"
                            : t("adminStats.medianAgeDays", {
                                  days: stats.unreviewed_median_age_days.toFixed(1),
                              })
                    }
                />
                <Metric
                    label={t("adminStats.anonymousIps")}
                    value={String(stats.anonymous_ip_buckets_24h)}
                />
            </div>

            <Card className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b border-gray-200 text-left text-gray-500">
                            <th className="py-2 pr-3 font-medium">
                                {t("adminStats.colDay")}
                            </th>
                            <th className="py-2 pr-3 font-medium">
                                {t("adminStats.colGenerations")}
                            </th>
                            <th className="py-2 pr-3 font-medium">
                                {t("adminStats.colAsks")}
                            </th>
                            <th className="py-2 pr-3 font-medium">
                                {t("adminStats.colCacheHits")}
                            </th>
                            <th className="py-2 font-medium">
                                {t("adminStats.colUsers")}
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {stats.daily.map((row) => (
                            <tr
                                key={row.day}
                                className="border-b border-gray-100 text-gray-900"
                            >
                                <td className="py-1.5 pr-3">
                                    {new Date(row.day).toLocaleDateString(locale)}
                                </td>
                                <td className="py-1.5 pr-3">{row.generations}</td>
                                <td className="py-1.5 pr-3">{row.asks}</td>
                                <td className="py-1.5 pr-3">{row.cache_hits}</td>
                                <td className="py-1.5">{row.distinct_users}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </Card>

            <p className="text-xs text-gray-500">
                {t("adminStats.generationsHint")}
            </p>

            <ReviewAgreementSection />
        </main>
    );
}
