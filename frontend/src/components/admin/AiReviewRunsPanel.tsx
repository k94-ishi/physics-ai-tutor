"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchAiReviewPendingCount, fetchAiReviewRuns } from "@/lib/api";
import {
    AiReviewPendingCount,
    AiReviewRun,
    AiReviewRunStatus,
} from "@/types/aiReviewRun";
import { useAiReviewRun } from "@/lib/hooks/useAiReviewRun";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import StatusMessage from "@/components/ui/StatusMessage";
import { showToast } from "@/components/ui/Toast";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { TranslationKey } from "@/lib/i18n/translations";

const STATUS_KEYS: Record<AiReviewRunStatus, TranslationKey> = {
    running: "aiRuns.status.running",
    done: "aiRuns.status.done",
    failed: "aiRuns.status.failed",
    cancelled: "aiRuns.status.cancelled",
};

const STATUS_CLASSES: Record<AiReviewRunStatus, string> = {
    running: "bg-blue-50 text-blue-700",
    done: "bg-green-50 text-green-700",
    failed: "bg-red-50 text-red-700",
    cancelled: "bg-gray-100 text-gray-500",
};

type AiReviewRunsPanelProps = {
    /** ラン完了後に親が集計(合意率など)を取り直すためのフック。 */
    onRunFinished?: () => void;
};

/**
 * /admin/stats のAIレビュー実行パネル([27])。
 * 未判定・旧プロンプト件数と残り回数を見せ、確認ダイアログでDeepSeek
 * 呼び出し回数を明示してからランを開始し、終わるまで進捗を出す。
 */
export default function AiReviewRunsPanel({
    onRunFinished,
}: AiReviewRunsPanelProps) {
    const { language, t } = useLanguage();
    const [counts, setCounts] = useState<AiReviewPendingCount | null>(null);
    const [recent, setRecent] = useState<AiReviewRun[]>([]);
    const [error, setError] = useState(false);
    const [confirmScope, setConfirmScope] = useState<"pending" | "stale" | null>(
        null
    );

    const load = useCallback(async () => {
        setError(false);
        try {
            const [nextCounts, nextRuns] = await Promise.all([
                fetchAiReviewPendingCount(),
                fetchAiReviewRuns(10),
            ]);
            setCounts(nextCounts);
            setRecent(nextRuns);
            return nextRuns;
        } catch (error) {
            console.error(error);
            setError(true);
            return [];
        }
    }, []);

    const { run, running, starting, start, adopt } = useAiReviewRun(
        (finished) => {
            if (finished.status === "done") {
                showToast(
                    t("aiRuns.finishedToast", {
                        reviewed: finished.reviewed_count,
                        skipped: finished.skipped_count,
                        failed: finished.failed_count,
                    })
                );
            } else {
                showToast(
                    t("aiRuns.failedToast", { error: finished.error ?? "?" }),
                    "error"
                );
            }
            load();
            onRunFinished?.();
        }
    );

    useEffect(() => {
        (async () => {
            const runs = await load();
            // 他の画面やCLIが始めたランが動いていたら進捗表示を引き継ぐ。
            const active = runs.find((r) => r.status === "running");
            if (active) {
                adopt(active);
            }
        })();
    }, [load, adopt]);

    if (error) {
        return (
            <StatusMessage
                variant="error"
                message={t("aiRuns.fetchFailed")}
                onRetry={load}
            />
        );
    }

    if (counts === null) {
        return null;
    }

    const wouldReview =
        confirmScope === "stale"
            ? counts.would_review_stale
            : counts.would_review_pending;
    const processed = run
        ? run.reviewed_count + run.skipped_count + run.failed_count
        : 0;
    const progressPercent =
        run && run.requested_count > 0
            ? Math.round((processed / run.requested_count) * 100)
            : 100;
    const noBudget = counts.remaining <= 0;
    const disabled = running || starting || noBudget;
    const disabledReason = running
        ? t("aiRuns.disabledRunning")
        : noBudget
          ? t("aiRuns.disabledNoBudget")
          : counts.would_review_pending === 0
            ? t("aiRuns.nothingPending")
            : null;
    const locale = language === "ja" ? "ja-JP" : "en-US";

    return (
        <Card className="flex flex-col gap-4">
            <h2 className="text-lg font-semibold text-gray-900">
                {t("aiRuns.heading")}
            </h2>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="flex flex-col gap-1">
                    <span className="text-xs text-gray-500">
                        {t("aiRuns.pendingCount")}
                    </span>
                    <span className="text-xl font-semibold text-gray-900">
                        {counts.pending}
                    </span>
                </div>
                <div className="flex flex-col gap-1">
                    <span className="text-xs text-gray-500">
                        {t("aiRuns.staleCount")}
                    </span>
                    <span className="text-xl font-semibold text-gray-900">
                        {counts.stale}
                    </span>
                </div>
                <div className="flex flex-col gap-1">
                    <span className="text-xs text-gray-500">{t("aiRuns.budget")}</span>
                    <span className="text-xl font-semibold text-gray-900">
                        {t("aiRuns.budgetValue", {
                            remaining: counts.remaining,
                            cap: counts.daily_cap,
                        })}
                    </span>
                </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
                <Button
                    type="button"
                    disabled={disabled || counts.would_review_pending === 0}
                    onClick={() => setConfirmScope("pending")}
                >
                    {t("aiRuns.reviewAllPending")}
                </Button>
                {counts.stale > 0 && (
                    <Button
                        type="button"
                        variant="secondary"
                        disabled={disabled || counts.would_review_stale === 0}
                        onClick={() => setConfirmScope("stale")}
                    >
                        {t("aiRuns.reReviewStale")}
                    </Button>
                )}
                {disabledReason && (
                    <span className="text-xs text-gray-500">{disabledReason}</span>
                )}
            </div>

            {run && running && (
                <div className="flex flex-col gap-1" role="status">
                    <span className="text-sm text-gray-700">
                        {t("aiRuns.progress", {
                            processed,
                            requested: run.requested_count,
                        })}
                    </span>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100">
                        <div
                            className="h-full rounded-full bg-blue-500 transition-all"
                            style={{ width: `${progressPercent}%` }}
                        />
                    </div>
                </div>
            )}

            <div className="flex flex-col gap-2">
                <h3 className="text-sm font-medium text-gray-700">
                    {t("aiRuns.recentHeading")}
                </h3>
                {recent.length === 0 ? (
                    <p className="text-sm text-gray-500">{t("aiRuns.noRuns")}</p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-gray-200 text-left text-gray-500">
                                    <th className="py-2 pr-3 font-medium">
                                        {t("aiRuns.colStarted")}
                                    </th>
                                    <th className="py-2 pr-3 font-medium">
                                        {t("aiRuns.colTrigger")}
                                    </th>
                                    <th className="py-2 pr-3 font-medium">
                                        {t("aiRuns.colScope")}
                                    </th>
                                    <th className="py-2 pr-3 font-medium">
                                        {t("aiRuns.colResult")}
                                    </th>
                                    <th className="py-2 pr-3 font-medium">
                                        {t("aiRuns.colTokens")}
                                    </th>
                                    <th className="py-2 pr-3 font-medium">
                                        {t("aiRuns.colStatus")}
                                    </th>
                                    <th className="py-2 font-medium">
                                        {t("aiRuns.colUser")}
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                {recent.map((row) => (
                                    <tr
                                        key={row.id}
                                        className="border-b border-gray-100 text-gray-900"
                                    >
                                        <td className="py-1.5 pr-3 whitespace-nowrap">
                                            {new Date(row.started_at).toLocaleString(
                                                locale
                                            )}
                                        </td>
                                        <td className="py-1.5 pr-3">{row.trigger}</td>
                                        <td className="py-1.5 pr-3">{row.scope}</td>
                                        <td className="py-1.5 pr-3 whitespace-nowrap">
                                            {t("aiRuns.resultCell", {
                                                reviewed: row.reviewed_count,
                                                skipped: row.skipped_count,
                                                failed: row.failed_count,
                                                requested: row.requested_count,
                                            })}
                                        </td>
                                        <td className="py-1.5 pr-3">
                                            {row.prompt_tokens + row.completion_tokens}
                                        </td>
                                        <td className="py-1.5 pr-3">
                                            <span
                                                className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_CLASSES[row.status]}`}
                                                title={row.error ?? undefined}
                                            >
                                                {t(STATUS_KEYS[row.status])}
                                            </span>
                                        </td>
                                        <td className="py-1.5">
                                            {row.started_by_user_id ?? "—"}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            <ConfirmDialog
                open={confirmScope !== null}
                title={t("aiRuns.confirmTitle")}
                description={t("aiRuns.confirmCalls", { count: wouldReview })}
                confirmLabel={t("aiRuns.startLabel")}
                confirming={starting}
                onConfirm={async () => {
                    if (confirmScope === null) {
                        return;
                    }
                    const created = await start(confirmScope);
                    setConfirmScope(null);
                    if (created) {
                        setRecent((prev) => [created, ...prev].slice(0, 10));
                    }
                }}
                onCancel={() => setConfirmScope(null)}
            />
        </Card>
    );
}
