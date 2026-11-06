"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, fetchAiReviewRun, startAiReviewRun } from "@/lib/api";
import { AiReviewRun, AiReviewRunScope } from "@/types/aiReviewRun";
import { showToast } from "@/components/ui/Toast";
import { useLanguage } from "@/lib/i18n/LanguageContext";

export const RUN_POLL_INTERVAL_MS = 2500;

/**
 * AIレビュー実行の開始とポーリングをまとめたフック([27][28]で共用)。
 * 409(実行中)と429(日次上限)はトーストにして呼び出し側へはnullを返す。
 * 実行中はRUN_POLL_INTERVAL_MSごとに進捗を取り直し、終わったら
 * onFinishedを一度だけ呼ぶ。
 */
export function useAiReviewRun(onFinished?: (run: AiReviewRun) => void) {
    const { t } = useLanguage();
    const [run, setRun] = useState<AiReviewRun | null>(null);
    const [starting, setStarting] = useState(false);

    // 毎ポーリングでeffectを張り直さないよう、最新のコールバックだけ持つ。
    const onFinishedRef = useRef(onFinished);
    useEffect(() => {
        onFinishedRef.current = onFinished;
    }, [onFinished]);

    const running = run?.status === "running";
    const runId = run?.id;

    useEffect(() => {
        if (runId === undefined || !running) {
            return;
        }

        let cancelled = false;
        const timer = setInterval(async () => {
            try {
                const next = await fetchAiReviewRun(runId);
                if (cancelled) {
                    return;
                }
                setRun(next);
                if (next.status !== "running") {
                    onFinishedRef.current?.(next);
                }
            } catch (error) {
                // 一時的な取得失敗は次のポーリングに任せる。
                console.error(error);
            }
        }, RUN_POLL_INTERVAL_MS);

        return () => {
            cancelled = true;
            clearInterval(timer);
        };
    }, [runId, running]);

    const start = useCallback(
        async (
            scope: AiReviewRunScope,
            questionIds?: number[]
        ): Promise<AiReviewRun | null> => {
            setStarting(true);
            try {
                const created = await startAiReviewRun({ scope, questionIds });
                setRun(created);
                if (created.status !== "running") {
                    onFinishedRef.current?.(created);
                }
                return created;
            } catch (error) {
                if (error instanceof ApiError && error.status === 409) {
                    showToast(t("aiRuns.alreadyRunning"), "error");
                } else if (error instanceof ApiError && error.status === 429) {
                    showToast(t("aiRuns.capExhausted"), "error");
                } else {
                    console.error(error);
                    showToast(t("aiRuns.startFailed"), "error");
                }
                return null;
            } finally {
                setStarting(false);
            }
        },
        [t]
    );

    // 他の場所(直近一覧など)で見つけた実行中ランをこのフックに引き継ぐ。
    const adopt = useCallback((existing: AiReviewRun) => {
        setRun((prev) => (prev?.id === existing.id ? prev : existing));
    }, []);

    return { run, running, starting, start, adopt };
}
