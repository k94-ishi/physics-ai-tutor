"use client";

import { FormEvent, Suspense, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
    fetchQuestions,
    searchQuestions,
    deleteQuestion,
    reviewQuestion,
    bulkDeleteQuestions,
    bulkReviewQuestions,
    extractConcepts,
    translateQuestions,
} from "@/lib/api";
import {
    AiVerdict,
    AiVerdictFilter,
    Question,
    QuestionSort,
    QuestionStatus,
    ReviewReason,
    SimilarQuestion,
} from "@/types/question";
import Card from "@/components/ui/Card";
import Button, { buttonClassName } from "@/components/ui/Button";
import SelectField from "@/components/ui/SelectField";
import LoadingState from "@/components/ui/LoadingState";
import StatusMessage from "@/components/ui/StatusMessage";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import ReviewReasonDialog, {
    reasonLabelKey,
} from "@/components/ui/ReviewReasonDialog";
import Pagination from "@/components/ui/Pagination";
import MarkdownContent from "@/components/ui/MarkdownContent";
import ReferencedQuestions from "@/components/ui/ReferencedQuestions";
import { showToast } from "@/components/ui/Toast";
import { useQueryState } from "@/lib/hooks/useQueryState";
import { runWithConcurrencyLimit } from "@/lib/concurrency";
import { parseIdSearch } from "@/lib/questionIds";
import { useAiReviewRun } from "@/lib/hooks/useAiReviewRun";
import {
    isAiReviewable,
    splitAiReviewSelection,
} from "@/lib/aiReviewEligibility";
import QuestionIdBadge from "@/components/ui/QuestionIdBadge";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { TranslationKey } from "@/lib/i18n/translations";

type Mode = "ai" | "keyword";
type BulkAction =
    | "delete"
    | "approve"
    | "reject"
    | "extract"
    | "translate"
    | "aiReview";
type ConceptFilter = "" | "extracted" | "unextracted";

// URL由来の値は何でもあり得るので、候補と突き合わせてから型に入れる。
// 候補外(?sort=garbage等)は既定値扱いにし、APIへ渡して422にしない。
function fromUrl<T extends string>(value: string, allowed: readonly T[]): T | "" {
    return (allowed as readonly string[]).includes(value) ? (value as T) : "";
}

const STATUS_VALUES: readonly QuestionStatus[] = [
    "UNREVIEWED",
    "APPROVED",
    "REJECTED",
];
const CONCEPT_FILTER_VALUES: readonly ConceptFilter[] = [
    "extracted",
    "unextracted",
];
const SORT_VALUES: readonly QuestionSort[] = [
    "oldest",
    "ai_confidence",
    "asked_count",
];
const AI_VERDICT_VALUES: readonly AiVerdictFilter[] = [
    "APPROVE",
    "EDIT",
    "REJECT",
    "NONE",
];
type ExtractionStatus = "processing" | "done" | "error";
type ReviewAction = "APPROVE" | "REJECT";
type ReviewActionState = { action: ReviewAction; state: "processing" | "error" };

const SIMILARITY_LIMIT = 10;
const KEYWORD_DEBOUNCE_MS = 300;

const ADMIN_QUERY_DEFAULTS = {
    page: "1",
    size: "30",
    keyword: "",
    ids: "",
    status: "",
    conceptFilter: "",
    sort: "",
    aiVerdict: "",
};

const AI_VERDICT_SHORT_KEYS: Record<AiVerdict, TranslationKey> = {
    APPROVE: "admin.aiShortApprove",
    EDIT: "admin.aiShortEdit",
    REJECT: "admin.aiShortReject",
};

const AI_VERDICT_BADGE_CLASSES: Record<AiVerdict | "UNPARSED", string> = {
    APPROVE: "bg-green-50 text-green-700",
    EDIT: "bg-yellow-50 text-yellow-800",
    REJECT: "bg-red-50 text-red-700",
    UNPARSED: "bg-gray-100 text-gray-500",
};

const STATUS_LABEL_KEYS: Record<QuestionStatus, TranslationKey> = {
    UNREVIEWED: "admin.status.unreviewed",
    APPROVED: "admin.status.approved",
    REJECTED: "admin.status.rejected",
};

const STATUS_BADGE_CLASSES: Record<QuestionStatus, string> = {
    UNREVIEWED: "bg-yellow-50 text-yellow-700",
    APPROVED: "bg-green-50 text-green-700",
    REJECTED: "bg-red-50 text-red-700",
};

const BULK_ACTION_KEYS: Record<
    BulkAction,
    { title: TranslationKey; confirmLabel: TranslationKey }
> = {
    delete: { title: "admin.confirmBulkDelete", confirmLabel: "common.delete" },
    approve: { title: "admin.confirmBulkApprove", confirmLabel: "common.approve" },
    reject: { title: "admin.confirmBulkReject", confirmLabel: "common.reject" },
    extract: { title: "admin.confirmBulkExtract", confirmLabel: "admin.extractLabel" },
    translate: {
        title: "admin.confirmBulkTranslate",
        confirmLabel: "admin.translateLabel",
    },
    aiReview: {
        title: "admin.aiReviewBulkTitle",
        confirmLabel: "admin.bulkAiReview",
    },
};

function modeButtonClassName(active: boolean): string {
    return `rounded-md px-4 py-2 text-sm font-medium transition-colors ${
        active
            ? "bg-blue-600 text-white"
            : "border border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
    }`;
}

function similarityPercent(distance: number): number {
    return Math.max(0, Math.round((1 - distance) * 100));
}

const inputClassName =
    "w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

function AdminQuestionsPageInner() {
    const { t } = useLanguage();
    const [mode, setMode] = useState<Mode>("keyword");

    // 一覧(pagination + keyword filter + status filter、URLで管理)
    const [queryState, setQueryState] = useQueryState(ADMIN_QUERY_DEFAULTS);
    const page = Number(queryState.page);
    const size = Number(queryState.size);
    const statusFilter = fromUrl(queryState.status, STATUS_VALUES);
    const conceptFilter = fromUrl(queryState.conceptFilter, CONCEPT_FILTER_VALUES);
    const sortOption = fromUrl(queryState.sort, SORT_VALUES);
    const aiVerdictFilter = fromUrl(queryState.aiVerdict, AI_VERDICT_VALUES);
    const [keywordInput, setKeywordInput] = useState(queryState.keyword);
    const [listItems, setListItems] = useState<Question[]>([]);
    const [listTotal, setListTotal] = useState(0);
    const [listLoading, setListLoading] = useState(true);
    const [listError, setListError] = useState(false);
    const listRequestId = useRef(0);

    // AI関連度検索(送信時のみ実行)
    const [similarityInput, setSimilarityInput] = useState("");
    const [similaritySearched, setSimilaritySearched] = useState(false);
    const [similarityResults, setSimilarityResults] = useState<SimilarQuestion[]>([]);
    const [similarityLoading, setSimilarityLoading] = useState(false);
    const [similarityError, setSimilarityError] = useState(false);
    const similarityRequestId = useRef(0);

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
    const [aiReviewingIds, setAiReviewingIds] = useState<Set<number>>(new Set());
    const aiReviewBatchRef = useRef<number[]>([]);

    // 単体操作(削除のみ確認ダイアログを経由し、承認・却下は即実行)
    const [deleteTarget, setDeleteTarget] = useState<Question | null>(null);
    const [deleting, setDeleting] = useState(false);

    // 承認/却下は非同期化し、ダイアログは即座に閉じてカードごとにバッジで進捗を表示する
    const [reviewStatus, setReviewStatus] = useState<
        Map<number, ReviewActionState>
    >(new Map());
    const reviewingIdsRef = useRef<Set<number>>(new Set());

    const loadList = useCallback(
        async (
            targetPage: number,
            targetSize: number,
            keyword: string,
            status: QuestionStatus | "",
            sort: QuestionSort | "" = "",
            aiVerdict: AiVerdictFilter | "" = "",
            ids: string = ""
        ) => {
            const requestId = ++listRequestId.current;
            setListLoading(true);
            setListError(false);

            try {
                const idFilter = parseIdSearch(ids);
                const data = await fetchQuestions({
                    page: targetPage,
                    size: targetSize,
                    keyword: keyword || undefined,
                    status: status || undefined,
                    sort: sort || undefined,
                    aiVerdict: aiVerdict || undefined,
                    ids: idFilter ?? undefined,
                });

                if (requestId !== listRequestId.current) {
                    return;
                }

                setListItems(data.items);
                setListTotal(data.total);
            } catch (error) {
                if (requestId !== listRequestId.current) {
                    return;
                }

                console.error(error);
                setListError(true);
            } finally {
                if (requestId === listRequestId.current) {
                    setListLoading(false);
                }
            }
        },
        []
    );

    // URLのkeyword/idsが外部要因(戻る/進む、?ids=の直リンク等)で変わったら
    // 入力欄に反映する。id検索は "#54,848" の形に戻すとそのまま再解析できる。
    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setKeywordInput(
            queryState.ids ? `#${queryState.ids}` : queryState.keyword
        );
    }, [queryState.keyword, queryState.ids]);

    // キーワード入力をデバウンスしてURLへ反映する(1ページ目に戻す)。
    // "#54" や "54,848" はキーワードではなくid検索としてidsへ送る。
    useEffect(() => {
        const timer = setTimeout(() => {
            const trimmed = keywordInput.trim();
            const ids = parseIdSearch(trimmed);
            const nextIds = ids ? ids.join(",") : "";
            const nextKeyword = ids ? "" : trimmed;

            if (
                nextKeyword !== queryState.keyword ||
                nextIds !== queryState.ids
            ) {
                setQueryState({
                    keyword: nextKeyword,
                    ids: nextIds,
                    page: "1",
                });
            }
        }, KEYWORD_DEBOUNCE_MS);

        return () => clearTimeout(timer);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [keywordInput]);

    // 検索条件・ページが変わったら選択状態をリセットする
    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setSelectedIds(new Set());
    }, [
        queryState.keyword,
        queryState.ids,
        statusFilter,
        conceptFilter,
        sortOption,
        aiVerdictFilter,
        page,
    ]);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        loadList(page, size, queryState.keyword, statusFilter, sortOption, aiVerdictFilter, queryState.ids);
    }, [
        loadList,
        page,
        size,
        queryState.keyword,
        queryState.ids,
        statusFilter,
        sortOption,
        aiVerdictFilter,
    ]);

    const runSimilaritySearch = useCallback(async (query: string) => {
        const trimmed = query.trim();

        if (!trimmed) {
            return;
        }

        const requestId = ++similarityRequestId.current;
        setSimilaritySearched(true);
        setSimilarityLoading(true);
        setSimilarityError(false);

        try {
            const results = await searchQuestions({
                query: trimmed,
                limit: SIMILARITY_LIMIT,
            });

            if (requestId !== similarityRequestId.current) {
                return;
            }

            setSimilarityResults(results);
        } catch (error) {
            if (requestId !== similarityRequestId.current) {
                return;
            }

            console.error(error);
            setSimilarityError(true);
        } finally {
            if (requestId === similarityRequestId.current) {
                setSimilarityLoading(false);
            }
        }
    }, []);

    const handleSimilaritySubmit = (e: FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        runSimilaritySearch(similarityInput);
    };

    const showSimilarityView = mode === "ai" && similaritySearched;

    const visibleItems = listItems.filter((question) => {
        if (conceptFilter === "extracted") {
            return question.concepts.length > 0;
        }
        if (conceptFilter === "unextracted") {
            return question.concepts.length === 0;
        }
        return true;
    });

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
                : new Set(visibleItems.map((q) => q.id))
        );
    };

    const handleConfirmDelete = async () => {
        if (!deleteTarget) {
            return;
        }

        setDeleting(true);

        try {
            await deleteQuestion(deleteTarget.id);
            await loadList(page, size, queryState.keyword, statusFilter, sortOption, aiVerdictFilter, queryState.ids);
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
        comment?: string
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
                    prev.map((q) => (q.id === question.id ? updated : q))
                );
                setReviewStatus((prev) => {
                    const next = new Map(prev);
                    next.delete(question.id);
                    return next;
                });
                showToast(
                    action === "APPROVE"
                        ? t("admin.questionApproved")
                        : t("admin.questionRejected")
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
        comment?: string
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
                    t("admin.bulkDeletedCount", { count: result.deleted_count })
                );
            } else if (bulkAction === "translate") {
                const { results } = await translateQuestions(ids);
                const successCount = results.filter((r) => r.success).length;
                showToast(
                    t("admin.bulkTranslatedCount", { count: successCount })
                );
            } else {
                const result = await bulkReviewQuestions(
                    ids,
                    bulkAction === "approve" ? "APPROVE" : "REJECT",
                    reason,
                    comment
                );
                showToast(
                    t(
                        bulkAction === "approve"
                            ? "admin.bulkApprovedCount"
                            : "admin.bulkRejectedCount",
                        { count: result.questions.length }
                    )
                );
            }

            setSelectedIds(new Set());
            setBulkAction(null);
            await loadList(page, size, queryState.keyword, statusFilter, sortOption, aiVerdictFilter, queryState.ids);
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
        const targetIds = ids.filter(
            (id) => !processingIdsRef.current.has(id)
        );

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
                                : question
                        )
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
                })
            );
        } else {
            showToast(
                t("aiRuns.failedToast", { error: finished.error ?? "?" }),
                "error"
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

    const handlePageChange = (nextPage: number) =>
        setQueryState({ page: String(nextPage) });
    const handleSizeChange = (nextSize: number) =>
        setQueryState({ size: String(nextSize), page: "1" });

    return (
        <main className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-gray-900">
                    {t("header.questionManagement")}
                </h1>

                <div className="flex items-center gap-2">
                    <Link
                        href="/admin/questions/upload"
                        className={buttonClassName("secondary")}
                    >
                        {t("admin.uploadJsonl")}
                    </Link>

                    <Link
                        href="/admin/questions/new"
                        className={buttonClassName("primary")}
                    >
                        {t("admin.newQuestion")}
                    </Link>
                </div>
            </div>

            <div className="flex flex-wrap items-end gap-4">
                <div className="flex gap-2">
                    <button
                        type="button"
                        className={modeButtonClassName(mode === "ai")}
                        onClick={() => setMode("ai")}
                    >
                        {t("admin.similaritySearchMode")}
                    </button>

                    <button
                        type="button"
                        className={modeButtonClassName(mode === "keyword")}
                        onClick={() => setMode("keyword")}
                    >
                        {t("common.keywordSearch")}
                    </button>
                </div>

                {mode === "keyword" && (
                    <>
                        <div className="w-56">
                            <SelectField
                                id="status-filter"
                                label={t("admin.statusFilterLabel")}
                                value={statusFilter}
                                onChange={(e) =>
                                    setQueryState({
                                        status: e.target.value,
                                        page: "1",
                                    })
                                }
                                options={[
                                    { value: "", label: t("common.all") },
                                    {
                                        value: "UNREVIEWED",
                                        label: t("admin.status.unreviewed"),
                                    },
                                    {
                                        value: "APPROVED",
                                        label: t("admin.status.approved"),
                                    },
                                    {
                                        value: "REJECTED",
                                        label: t("admin.status.rejected"),
                                    },
                                ]}
                            />
                        </div>

                        <div className="w-56">
                            <SelectField
                                id="concept-filter"
                                label={t("admin.conceptFilterLabel")}
                                value={conceptFilter}
                                onChange={(e) =>
                                    setQueryState({
                                        conceptFilter: e.target.value,
                                    })
                                }
                                options={[
                                    { value: "", label: t("common.all") },
                                    {
                                        value: "extracted",
                                        label: t("admin.conceptExtracted"),
                                    },
                                    {
                                        value: "unextracted",
                                        label: t("admin.conceptUnextracted"),
                                    },
                                ]}
                            />
                        </div>

                        <div className="w-56">
                            <SelectField
                                id="ai-verdict-filter"
                                label={t("admin.aiVerdictFilterLabel")}
                                value={aiVerdictFilter}
                                onChange={(e) =>
                                    setQueryState({
                                        aiVerdict: e.target.value,
                                        page: "1",
                                    })
                                }
                                options={[
                                    { value: "", label: t("common.all") },
                                    { value: "REJECT", label: t("admin.aiVerdictReject") },
                                    { value: "EDIT", label: t("admin.aiVerdictEdit") },
                                    { value: "APPROVE", label: t("admin.aiVerdictApprove") },
                                    { value: "NONE", label: t("admin.aiVerdictNone") },
                                ]}
                            />
                        </div>

                        <div className="w-56">
                            <SelectField
                                id="sort-order"
                                label={t("admin.sortLabel")}
                                value={sortOption}
                                onChange={(e) =>
                                    setQueryState({
                                        sort: e.target.value,
                                        page: "1",
                                    })
                                }
                                options={[
                                    { value: "", label: t("admin.sortDefault") },
                                    { value: "oldest", label: t("admin.sortOldest") },
                                    {
                                        value: "ai_confidence",
                                        label: t("admin.sortAiConfidence"),
                                    },
                                    {
                                        value: "asked_count",
                                        label: t("admin.sortAskedCount"),
                                    },
                                ]}
                            />
                        </div>
                    </>
                )}
            </div>

            {mode === "ai" ? (
                <form
                    onSubmit={handleSimilaritySubmit}
                    className="flex gap-2"
                >
                    <input
                        type="text"
                        value={similarityInput}
                        onChange={(e) => setSimilarityInput(e.target.value)}
                        placeholder={t("questionSearch.placeholder")}
                        className={inputClassName}
                    />

                    <Button
                        type="submit"
                        disabled={similarityLoading || !similarityInput.trim()}
                        className="shrink-0"
                    >
                        {t("common.search")}
                    </Button>
                </form>
            ) : (
                <input
                    type="text"
                    value={keywordInput}
                    onChange={(e) => setKeywordInput(e.target.value)}
                    placeholder={t("admin.keywordPlaceholder")}
                    className={inputClassName}
                />
            )}

            {showSimilarityView ? (
                <>
                    {similarityLoading && <LoadingState label={t("common.searching")} />}

                    {!similarityLoading && similarityError && (
                        <StatusMessage
                            variant="error"
                            message={t("common.searchFailed")}
                            onRetry={() => runSimilaritySearch(similarityInput)}
                        />
                    )}

                    {!similarityLoading &&
                        !similarityError &&
                        similarityResults.length === 0 && (
                            <StatusMessage message={t("questionSearch.noResults")} />
                        )}

                    {!similarityLoading &&
                        !similarityError &&
                        similarityResults.length > 0 && (
                            <div className="flex flex-col gap-3">
                                {similarityResults.map((result) => (
                                    <Link
                                        key={result.id}
                                        href={`/admin/questions/${result.id}/edit`}
                                    >
                                        <Card className="transition-colors hover:border-blue-300 hover:bg-blue-50/50">
                                            <div className="flex items-start justify-between gap-3">
                                                <span className="font-medium text-gray-900">
                                                    {result.question}
                                                </span>

                                                <span className="shrink-0 rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                                                    {t("questionSearch.relevance")}{" "}
                                                    {similarityPercent(result.distance)}%
                                                </span>
                                            </div>

                                            <MarkdownContent
                                                content={result.answer}
                                                variant="full"
                                            />
                                        </Card>
                                    </Link>
                                ))}
                            </div>
                        )}
                </>
            ) : (
                <>
                    {listLoading && <LoadingState />}

                    {!listLoading && listError && (
                        <StatusMessage
                            variant="error"
                            message={t("admin.fetchFailed")}
                            onRetry={() =>
                                loadList(page, size, queryState.keyword, statusFilter, sortOption, aiVerdictFilter, queryState.ids)
                            }
                        />
                    )}

                    {!listLoading && !listError && listItems.length === 0 && (
                        <StatusMessage message={t("questionList.empty")} />
                    )}

                    {!listLoading &&
                        !listError &&
                        listItems.length > 0 &&
                        visibleItems.length === 0 && (
                            <StatusMessage message={t("admin.noConceptMatch")} />
                        )}

                    {!listLoading && !listError && visibleItems.length > 0 && (
                        <>
                            <Pagination
                                page={page}
                                size={size}
                                total={listTotal}
                                onPageChange={handlePageChange}
                                onSizeChange={handleSizeChange}
                            />

                            <div className="flex flex-wrap items-center gap-3">
                                <label className="flex items-center gap-2 text-sm text-gray-600">
                                    <input
                                        type="checkbox"
                                        checked={
                                            selectedIds.size > 0 &&
                                            selectedIds.size === visibleItems.length
                                        }
                                        onChange={toggleSelectAll}
                                    />
                                    {selectedIds.size > 0
                                        ? t("common.selectedCount", {
                                              count: selectedIds.size,
                                          })
                                        : t("common.selectAll")}
                                </label>

                                {selectedIds.size > 0 && (
                                    <div className="ml-auto flex flex-wrap gap-2">
                                        <Button
                                            variant="secondary"
                                            onClick={() => setBulkAction("approve")}
                                        >
                                            {t("admin.bulkApprove")}
                                        </Button>
                                        <Button
                                            variant="secondary"
                                            onClick={() => setBulkAction("reject")}
                                        >
                                            {t("admin.bulkReject")}
                                        </Button>
                                        <Button
                                            variant="secondary"
                                            onClick={() => setBulkAction("extract")}
                                        >
                                            {t("admin.extractConcepts")}
                                        </Button>
                                        <Button
                                            variant="secondary"
                                            onClick={() =>
                                                setBulkAction("translate")
                                            }
                                        >
                                            {t("admin.translateLabel")}
                                        </Button>
                                        <Button
                                            variant="secondary"
                                            disabled={aiRun.running || aiRun.starting}
                                            onClick={() => setBulkAction("aiReview")}
                                        >
                                            {t("admin.bulkAiReview")}
                                        </Button>
                                        <Button
                                            variant="danger"
                                            onClick={() => setBulkAction("delete")}
                                        >
                                            {t("admin.bulkDelete")}
                                        </Button>
                                    </div>
                                )}
                            </div>

                            <ul className="flex flex-col gap-3">
                                {visibleItems.map((question) => {
                                    const hasConcepts = question.concepts.length > 0;
                                    const isSelected = selectedIds.has(question.id);
                                    const extraction = extractionStatus.get(question.id);
                                    const review = reviewStatus.get(question.id);

                                    return (
                                        <li key={question.id}>
                                            <Card
                                                onClick={() => toggleSelected(question.id)}
                                                className={`flex cursor-pointer items-start gap-3 transition-colors ${
                                                    isSelected
                                                        ? "border-blue-400 bg-blue-50/40"
                                                        : "hover:border-gray-300"
                                                }`}
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={isSelected}
                                                    onChange={() => toggleSelected(question.id)}
                                                    onClick={(e) => e.stopPropagation()}
                                                    className="mt-1 shrink-0"
                                                    aria-label={t("admin.selectQuestion", {
                                                        question: question.question,
                                                    })}
                                                />

                                                <div className="flex min-w-0 flex-1 flex-col gap-2">
                                                    <div className="flex flex-wrap items-center gap-2">
                                                        <QuestionIdBadge
                                                            id={question.id}
                                                        />

                                                        <span
                                                            className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE_CLASSES[question.status]}`}
                                                        >
                                                            {t(STATUS_LABEL_KEYS[question.status])}
                                                        </span>

                                                        {question.source === "RAG_RESULT" && (
                                                            <span className="shrink-0 rounded-full bg-purple-50 px-2 py-0.5 text-xs font-medium text-purple-700">
                                                                {t("admin.ragGenerated")}
                                                            </span>
                                                        )}

                                                        {(["ja", "en"] as const).map(
                                                            (lang) => {
                                                                const text =
                                                                    question.texts[lang];
                                                                return (
                                                                    <span
                                                                        key={lang}
                                                                        className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                                                                            text
                                                                                ? "bg-gray-100 text-gray-700"
                                                                                : "bg-gray-50 text-gray-400 line-through"
                                                                        }`}
                                                                        title={
                                                                            text?.provenance ===
                                                                            "MACHINE"
                                                                                ? t(
                                                                                      "admin.machineProvenance"
                                                                                  )
                                                                                : undefined
                                                                        }
                                                                    >
                                                                        {lang.toUpperCase()}
                                                                        {text?.provenance ===
                                                                            "MACHINE" && "*"}
                                                                    </span>
                                                                );
                                                            }
                                                        )}

                                                        <span
                                                            className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                                                                hasConcepts
                                                                    ? "bg-blue-50 text-blue-700"
                                                                    : "bg-gray-100 text-gray-500"
                                                            }`}
                                                        >
                                                            {hasConcepts
                                                                ? t("admin.conceptsExtractedCount", {
                                                                      count: question.concepts.length,
                                                                  })
                                                                : t("admin.conceptsNotExtracted")}
                                                        </span>

                                                        {extraction === "processing" && (
                                                            <span className="shrink-0 animate-pulse rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                                                                {t("admin.extractionProcessing")}
                                                            </span>
                                                        )}

                                                        {extraction === "done" && (
                                                            <span className="shrink-0 rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
                                                                {t("admin.extractionDone")}
                                                            </span>
                                                        )}

                                                        {extraction === "error" && (
                                                            <span className="shrink-0 rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
                                                                {t("admin.extractionFailed")}
                                                            </span>
                                                        )}

                                                        {question.ai_review && (
                                                            <span
                                                                className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                                                                    AI_VERDICT_BADGE_CLASSES[
                                                                        question.ai_review.verdict ??
                                                                            "UNPARSED"
                                                                    ]
                                                                }`}
                                                                title={
                                                                    question.ai_review.rationale ??
                                                                    undefined
                                                                }
                                                            >
                                                                AI:{" "}
                                                                {question.ai_review.verdict
                                                                    ? t(
                                                                          AI_VERDICT_SHORT_KEYS[
                                                                              question.ai_review.verdict
                                                                          ]
                                                                      )
                                                                    : t("admin.aiShortUnparsed")}
                                                                {question.ai_review.confidence !==
                                                                    null &&
                                                                    ` ${Math.round(
                                                                        question.ai_review.confidence * 100
                                                                    )}%`}
                                                                {question.ai_review.reasons[0] &&
                                                                    ` · ${t(
                                                                        reasonLabelKey(
                                                                            question.ai_review.reasons[0]
                                                                        )
                                                                    )}`}
                                                            </span>
                                                        )}

                                                        {question.physics_level !==
                                                            null && (
                                                            <span
                                                                className="shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700"
                                                                title={t("levels.badgeTitle", {
                                                                    p: question.physics_level,
                                                                    m: question.math_level ?? "-",
                                                                })}
                                                            >
                                                                {t("levels.badge", {
                                                                    p: question.physics_level,
                                                                    m: question.math_level ?? "-",
                                                                })}
                                                            </span>
                                                        )}

                                                        {aiReviewingIds.has(
                                                            question.id
                                                        ) && (
                                                            <span className="shrink-0 animate-pulse rounded-full bg-purple-50 px-2 py-0.5 text-xs font-medium text-purple-700">
                                                                {t("admin.aiReviewProcessing")}
                                                            </span>
                                                        )}

                                                        {review?.state === "processing" && (
                                                            <span className="shrink-0 animate-pulse rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                                                                {review.action === "APPROVE"
                                                                    ? t("admin.approving")
                                                                    : t("admin.rejecting")}
                                                            </span>
                                                        )}

                                                        {review?.state === "error" && (
                                                            <span className="shrink-0 rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
                                                                {review.action === "APPROVE"
                                                                    ? t("admin.approveFailed")
                                                                    : t("admin.rejectFailed")}
                                                            </span>
                                                        )}
                                                    </div>

                                                    <span className="font-medium text-gray-900">
                                                        {question.question}
                                                    </span>

                                                    {question.ai_review?.rationale && (
                                                        <details className="text-xs text-gray-600">
                                                            <summary className="cursor-pointer select-none text-gray-500">
                                                                {t("admin.aiRationaleToggle")}
                                                            </summary>
                                                            <p className="mt-1 whitespace-pre-wrap">
                                                                {question.ai_review.rationale}
                                                            </p>
                                                        </details>
                                                    )}

                                                    <MarkdownContent
                                                        content={question.answer}
                                                        variant="full"
                                                    />

                                                    {hasConcepts && (
                                                        <div className="flex flex-wrap gap-1">
                                                            {question.concepts.map((concept) => (
                                                                <span
                                                                    key={concept}
                                                                    className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
                                                                >
                                                                    {concept}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    )}

                                                    <ReferencedQuestions
                                                        items={question.retrieved_questions}
                                                    />

                                                    <div
                                                        className="flex flex-wrap items-center gap-2 pt-1"
                                                        onClick={(e) => e.stopPropagation()}
                                                    >
                                                        {question.status !== "APPROVED" && (
                                                            <Button
                                                                variant="secondary"
                                                                disabled={review?.state === "processing"}
                                                                onClick={() =>
                                                                    startReview(question, "APPROVE")
                                                                }
                                                            >
                                                                {t("common.approve")}
                                                            </Button>
                                                        )}

                                                        {question.status !== "REJECTED" && (
                                                            <Button
                                                                variant="secondary"
                                                                disabled={review?.state === "processing"}
                                                                onClick={() =>
                                                                    setRejectTarget(question)
                                                                }
                                                            >
                                                                {t("common.reject")}
                                                            </Button>
                                                        )}

                                                        <Link
                                                            href={`/admin/questions/${question.id}/reviews`}
                                                            className={buttonClassName("secondary")}
                                                        >
                                                            {t("common.history")}
                                                        </Link>

                                                        <Link
                                                            href={`/admin/questions/${question.id}/edit`}
                                                            className={buttonClassName("secondary")}
                                                        >
                                                            {t("common.edit")}
                                                        </Link>

                                                        {isAiReviewable(question) && (
                                                            <Button
                                                                variant="secondary"
                                                                disabled={
                                                                    aiRun.running ||
                                                                    aiRun.starting ||
                                                                    aiReviewingIds.has(
                                                                        question.id
                                                                    )
                                                                }
                                                                onClick={() =>
                                                                    startAiReviewSelected([
                                                                        question.id,
                                                                    ])
                                                                }
                                                            >
                                                                {question.ai_review
                                                                    ? t("admin.aiReviewCardAgain")
                                                                    : t("admin.aiReviewCard")}
                                                            </Button>
                                                        )}

                                                        <Button
                                                            variant="secondary"
                                                            disabled={extraction === "processing"}
                                                            onClick={() =>
                                                                startConceptExtraction([question.id])
                                                            }
                                                        >
                                                            {t("admin.extractConcepts")}
                                                        </Button>

                                                        <Button
                                                            variant="danger"
                                                            onClick={() => setDeleteTarget(question)}
                                                        >
                                                            {t("common.delete")}
                                                        </Button>
                                                    </div>
                                                </div>
                                            </Card>
                                        </li>
                                    );
                                })}
                            </ul>

                            <Pagination
                                page={page}
                                size={size}
                                total={listTotal}
                                onPageChange={handlePageChange}
                                onSizeChange={handleSizeChange}
                            />
                        </>
                    )}
                </>
            )}

            <ConfirmDialog
                open={deleteTarget !== null}
                title={t("admin.confirmDeleteQuestion")}
                description={deleteTarget?.question}
                confirming={deleting}
                onConfirm={handleConfirmDelete}
                onCancel={() => setDeleteTarget(null)}
            />

            <ConfirmDialog
                open={bulkAction !== null && bulkAction !== "reject"}
                title={bulkAction ? t(BULK_ACTION_KEYS[bulkAction].title) : ""}
                description={
                    bulkAction === "aiReview"
                        ? t("admin.aiReviewBulkDescription", {
                              eligible: aiSelection.eligibleIds.length,
                              skipped: aiSelection.skippedCount,
                          })
                        : t("admin.bulkTargetCount", { count: selectedIds.size })
                }
                confirmLabel={
                    bulkAction ? t(BULK_ACTION_KEYS[bulkAction].confirmLabel) : undefined
                }
                confirming={
                    bulkAction === "extract"
                        ? false
                        : bulkAction === "aiReview"
                          ? aiRun.starting
                          : bulkProcessing
                }
                onConfirm={() => {
                    if (bulkAction === "extract") {
                        startConceptExtraction(Array.from(selectedIds));
                    } else if (bulkAction === "aiReview") {
                        startAiReviewSelected(aiSelection.eligibleIds);
                    } else {
                        handleConfirmBulkAction();
                    }
                }}
                onCancel={() => setBulkAction(null)}
            />

            <ReviewReasonDialog
                open={rejectTarget !== null}
                title={t("reviewReason.dialogRejectTitle")}
                description={rejectTarget?.question}
                defaultReason={rejectTarget?.ai_review?.reasons[0]}
                onConfirm={(reason, comment) => {
                    if (rejectTarget !== null) {
                        startReview(rejectTarget, "REJECT", reason, comment);
                        setRejectTarget(null);
                    }
                }}
                onCancel={() => setRejectTarget(null)}
            />

            <ReviewReasonDialog
                open={bulkAction === "reject"}
                title={t("reviewReason.dialogRejectTitle")}
                description={t("admin.bulkTargetCount", { count: selectedIds.size })}
                confirming={bulkProcessing}
                onConfirm={(reason, comment) =>
                    handleConfirmBulkAction(reason, comment)
                }
                onCancel={() => setBulkAction(null)}
            />
        </main>
    );
}

export default function AdminQuestionsPage() {
    return (
        <Suspense fallback={<LoadingState />}>
            <AdminQuestionsPageInner />
        </Suspense>
    );
}
