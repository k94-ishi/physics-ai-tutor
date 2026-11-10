"use client";

import { useEffect, useRef, useState } from "react";
import {
    fetchQuestions,
    deleteQuestion,
    reviewQuestion,
    bulkDeleteQuestions,
    bulkReviewQuestions,
    extractConcepts,
    translateQuestions,
} from "@/lib/api";
import { Question, ReviewReason } from "@/types/question";
import { showToast } from "@/components/ui/Toast";
import { runWithConcurrencyLimit } from "@/lib/concurrency";
import { useAiReviewRun } from "@/lib/hooks/useAiReviewRun";
import { splitAiReviewSelection } from "@/lib/aiReviewEligibility";
import {
    ExtractionStatus,
    ReviewActionState,
} from "@/components/admin/AdminQuestionCard";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { AdminQueueList } from "@/app/admin/questions/useAdminQueueList";

export type BulkAction =
    "delete" | "approve" | "reject" | "extract" | "translate" | "aiReview";

// URL由来の値は何でもあり得るので、候補と突き合わせてから型に入れる。
// 候補外(?sort=garbage等)は既定値扱いにし、APIへ渡して422にしない。
type ReviewAction = "APPROVE" | "REJECT";

/** What a teacher does to rows: select, review, bulk, extract, AI review, delete ([63]). */
export function useAdminQueueActions({
    queryState,
    page,
    size,
    statusFilter,
    conceptFilter,
    sortOption,
    aiVerdictFilter,
    listItems,
    setListItems,
    loadList,
    visibleItems,
}: Pick<
    AdminQueueList,
    | "queryState"
    | "page"
    | "size"
    | "statusFilter"
    | "conceptFilter"
    | "sortOption"
    | "aiVerdictFilter"
    | "listItems"
    | "setListItems"
    | "loadList"
    | "visibleItems"
>) {
    const { t } = useLanguage();
    // 一覧(pagination + keyword filter + status filter、URLで管理)
    // AI関連度検索(送信時のみ実行)
    // 選択・一括操作(キーワード検索モードのみ)
    const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
    const [bulkAction, setBulkAction] = useState<BulkAction | null>(null);
    const [rejectTarget, setRejectTarget] = useState<Question | null>(null);
    const [bulkProcessing, setBulkProcessing] = useState(false);

    // Concept抽出は選択質問ごとに非同期(並列)で進めるため、状態はフロント側でのみ管理する
    const [extractionStatus, setExtractionStatus] = useState<
        Map<number, ExtractionStatus>
    >(new Map());
    const processingIdsRef = useRef<Set<number>>(new Set());

    // AIレビューはランとして実行し、対象カードに処理中バッジを出す([28])
    const [aiReviewingIds, setAiReviewingIds] = useState<Set<number>>(
        new Set(),
    );
    const aiReviewBatchRef = useRef<number[]>([]);

    // 単体操作(削除のみ確認ダイアログを経由し、承認・却下は即実行)
    const [deleteTarget, setDeleteTarget] = useState<Question | null>(null);
    const [deleting, setDeleting] = useState(false);

    // 承認/却下は非同期化し、ダイアログは即座に閉じてカードごとにバッジで進捗を表示する
    const [reviewStatus, setReviewStatus] = useState<
        Map<number, ReviewActionState>
    >(new Map());
    const reviewingIdsRef = useRef<Set<number>>(new Set());

    // URLのkeyword/idsが外部要因(戻る/進む、?ids=の直リンク等)で変わったら
    // 入力欄に反映する。id検索は "#54,848" の形に戻すとそのまま再解析できる。
    // キーワード入力をデバウンスしてURLへ反映する(1ページ目に戻す)。
    // "#54" や "54,848" はキーワードではなくid検索としてidsへ送る。
    // 検索条件・ページが変わったら選択状態をリセットする
    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setSelectedIds(new Set());
    }, [
        queryState.keyword,
        queryState.ids,
        queryState.concept,
        statusFilter,
        conceptFilter,
        sortOption,
        aiVerdictFilter,
        page,
    ]);

    const toggleSelected = (id: number) => {
        setSelectedIds((prev) => {
            const next = new Set(prev);
            if (next.has(id)) {
                next.delete(id);
            } else {
                next.add(id);
            }
            return next;
        });
    };

    const toggleSelectAll = () => {
        setSelectedIds((prev) =>
            prev.size === visibleItems.length
                ? new Set()
                : new Set(visibleItems.map((q) => q.id)),
        );
    };

    const handleConfirmDelete = async () => {
        if (!deleteTarget) {
            return;
        }

        setDeleting(true);

        try {
            await deleteQuestion(deleteTarget.id);
            await loadList(
                page,
                size,
                queryState.keyword,
                statusFilter,
                sortOption,
                aiVerdictFilter,
                queryState.ids,
                queryState.concept,
            );
            showToast(t("admin.questionDeleted"));
            setDeleteTarget(null);
        } catch (error) {
            console.error(error);
            showToast(t("admin.questionDeleteFailed"), "error");
        } finally {
            setDeleting(false);
        }
    };

    const startReview = (
        question: Question,
        action: ReviewAction,
        reason?: ReviewReason,
        comment?: string,
    ) => {
        if (reviewingIdsRef.current.has(question.id)) {
            return;
        }

        reviewingIdsRef.current.add(question.id);
        setReviewStatus((prev) => {
            const next = new Map(prev);
            next.set(question.id, { action, state: "processing" });
            return next;
        });

        (async () => {
            try {
                const updated = await reviewQuestion(question.id, {
                    action,
                    reason,
                    comment,
                });
                setListItems((prev) =>
                    prev.map((q) => (q.id === question.id ? updated : q)),
                );
                setReviewStatus((prev) => {
                    const next = new Map(prev);
                    next.delete(question.id);
                    return next;
                });
                showToast(
                    action === "APPROVE"
                        ? t("admin.questionApproved")
                        : t("admin.questionRejected"),
                );
            } catch (error) {
                console.error(error);
                setReviewStatus((prev) => {
                    const next = new Map(prev);
                    next.set(question.id, { action, state: "error" });
                    return next;
                });
                showToast(t("admin.actionFailed"), "error");
            } finally {
                reviewingIdsRef.current.delete(question.id);
            }
        })();
    };

    const handleConfirmBulkAction = async (
        reason?: ReviewReason,
        comment?: string,
    ) => {
        if (!bulkAction || bulkAction === "extract" || selectedIds.size === 0) {
            return;
        }

        setBulkProcessing(true);
        const ids = Array.from(selectedIds);

        try {
            if (bulkAction === "delete") {
                const result = await bulkDeleteQuestions(ids);
                showToast(
                    t("admin.bulkDeletedCount", {
                        count: result.deleted_count,
                    }),
                );
            } else if (bulkAction === "translate") {
                const { results } = await translateQuestions(ids);
                const successCount = results.filter((r) => r.success).length;
                showToast(
                    t("admin.bulkTranslatedCount", { count: successCount }),
                );
            } else {
                const result = await bulkReviewQuestions(
                    ids,
                    bulkAction === "approve" ? "APPROVE" : "REJECT",
                    reason,
                    comment,
                );
                showToast(
                    t(
                        bulkAction === "approve"
                            ? "admin.bulkApprovedCount"
                            : "admin.bulkRejectedCount",
                        { count: result.questions.length },
                    ),
                );
            }

            setSelectedIds(new Set());
            setBulkAction(null);
            await loadList(
                page,
                size,
                queryState.keyword,
                statusFilter,
                sortOption,
                aiVerdictFilter,
                queryState.ids,
                queryState.concept,
            );
        } catch (error) {
            console.error(error);
            showToast(t("admin.bulkActionFailed"), "error");
        } finally {
            setBulkProcessing(false);
        }
    };

    // Concept抽出は質問ごとに個別のAPI呼び出しを並列実行し、ダイアログはすぐ閉じて
    // 各カードのバッジ(処理中/完了/失敗)で進捗を表示する。全件完了を待たずに
    // 画面を操作できるようにするための非同期化(フロント側での状態管理)。
    const startConceptExtraction = (ids: number[]) => {
        const targetIds = ids.filter((id) => !processingIdsRef.current.has(id));

        setBulkAction(null);
        setSelectedIds(new Set());

        if (targetIds.length === 0) {
            return;
        }

        targetIds.forEach((id) => processingIdsRef.current.add(id));
        setExtractionStatus((prev) => {
            const next = new Map(prev);
            targetIds.forEach((id) => next.set(id, "processing"));
            return next;
        });

        runWithConcurrencyLimit(targetIds, 4, async (id) => {
            try {
                const { results } = await extractConcepts([id]);
                const result = results[0];

                setExtractionStatus((prev) => {
                    const next = new Map(prev);
                    next.set(id, result?.success ? "done" : "error");
                    return next;
                });

                if (result?.success) {
                    setListItems((prev) =>
                        prev.map((question) =>
                            question.id === id
                                ? { ...question, concepts: result.concepts }
                                : question,
                        ),
                    );
                }
            } catch (error) {
                console.error(error);
                setExtractionStatus((prev) => {
                    const next = new Map(prev);
                    next.set(id, "error");
                    return next;
                });
            } finally {
                processingIdsRef.current.delete(id);
            }
        });
    };

    // ランの完了時にまとめてトーストを出し、対象カードの判定バッジだけを
    // 取り直す(ページ全体は再読み込みしない)。
    const aiRun = useAiReviewRun(async (finished) => {
        const ids = aiReviewBatchRef.current;
        aiReviewBatchRef.current = [];
        setAiReviewingIds(new Set());

        if (finished.status === "done") {
            showToast(
                t("aiRuns.finishedToast", {
                    reviewed: finished.reviewed_count,
                    skipped: finished.skipped_count,
                    failed: finished.failed_count,
                }),
            );
        } else {
            showToast(
                t("aiRuns.failedToast", { error: finished.error ?? "?" }),
                "error",
            );
        }

        // idsフィルタは一度に100件まで([31])なので分割して取り直す。
        for (let index = 0; index < ids.length; index += 100) {
            const chunk = ids.slice(index, index + 100);
            try {
                const data = await fetchQuestions({
                    ids: chunk,
                    size: Math.min(Math.max(chunk.length, 1), 120),
                });
                setListItems((prev) => {
                    const byId = new Map(data.items.map((q) => [q.id, q]));
                    return prev.map((q) => byId.get(q.id) ?? q);
                });
            } catch (error) {
                console.error(error);
            }
        }
    });

    const startAiReviewSelected = async (ids: number[]) => {
        setBulkAction(null);

        if (ids.length === 0) {
            showToast(t("admin.aiReviewNothingEligible"), "error");
            return;
        }

        const created = await aiRun.start("selected", ids);
        if (created === null) {
            return;
        }

        setSelectedIds(new Set());
        aiReviewBatchRef.current = ids;
        setAiReviewingIds(new Set(ids));
    };

    const aiSelection = splitAiReviewSelection(listItems, selectedIds);

    return {
        selectedIds,
        bulkAction,
        setBulkAction,
        rejectTarget,
        setRejectTarget,
        bulkProcessing,
        extractionStatus,
        aiReviewingIds,
        deleteTarget,
        setDeleteTarget,
        deleting,
        reviewStatus,
        toggleSelected,
        toggleSelectAll,
        handleConfirmDelete,
        startReview,
        handleConfirmBulkAction,
        startConceptExtraction,
        aiRun,
        startAiReviewSelected,
        aiSelection,
    };
}
