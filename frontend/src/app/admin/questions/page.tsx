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
} from "@/lib/api";
import { Question, QuestionStatus, SimilarQuestion } from "@/types/question";
import Card from "@/components/ui/Card";
import Button, { buttonClassName } from "@/components/ui/Button";
import SelectField from "@/components/ui/SelectField";
import LoadingState from "@/components/ui/LoadingState";
import StatusMessage from "@/components/ui/StatusMessage";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import Pagination from "@/components/ui/Pagination";
import MarkdownContent from "@/components/ui/MarkdownContent";
import ReferencedQuestions from "@/components/ui/ReferencedQuestions";
import { showToast } from "@/components/ui/Toast";
import { useQueryState } from "@/lib/hooks/useQueryState";
import { runWithConcurrencyLimit } from "@/lib/concurrency";

type Mode = "ai" | "keyword";
type BulkAction = "delete" | "approve" | "reject" | "extract";
type ConceptFilter = "" | "extracted" | "unextracted";
type ExtractionStatus = "processing" | "done" | "error";
type ReviewAction = "APPROVE" | "REJECT";
type ReviewActionState = { action: ReviewAction; state: "processing" | "error" };

const SIMILARITY_LIMIT = 10;
const KEYWORD_DEBOUNCE_MS = 300;

const ADMIN_QUERY_DEFAULTS = {
    page: "1",
    size: "30",
    keyword: "",
    status: "",
    conceptFilter: "",
};

const STATUS_LABELS: Record<QuestionStatus, string> = {
    UNREVIEWED: "未レビュー",
    APPROVED: "承認済み",
    REJECTED: "却下",
};

const STATUS_BADGE_CLASSES: Record<QuestionStatus, string> = {
    UNREVIEWED: "bg-yellow-50 text-yellow-700",
    APPROVED: "bg-green-50 text-green-700",
    REJECTED: "bg-red-50 text-red-700",
};

const BULK_ACTION_LABELS: Record<BulkAction, { title: string; confirmLabel: string }> = {
    delete: { title: "選択した質問を削除しますか？", confirmLabel: "削除" },
    approve: { title: "選択した質問を承認しますか？", confirmLabel: "承認" },
    reject: { title: "選択した質問を却下しますか？", confirmLabel: "却下" },
    extract: { title: "選択した質問のConceptを抽出しますか？", confirmLabel: "抽出" },
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
    const [mode, setMode] = useState<Mode>("keyword");

    // 一覧(pagination + keyword filter + status filter、URLで管理)
    const [queryState, setQueryState] = useQueryState(ADMIN_QUERY_DEFAULTS);
    const page = Number(queryState.page);
    const size = Number(queryState.size);
    const statusFilter = queryState.status as QuestionStatus | "";
    const conceptFilter = queryState.conceptFilter as ConceptFilter;
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
    const [bulkProcessing, setBulkProcessing] = useState(false);

    // Concept抽出は選択質問ごとに非同期(並列)で進めるため、状態はフロント側でのみ管理する
    const [extractionStatus, setExtractionStatus] = useState<
        Map<number, ExtractionStatus>
    >(new Map());
    const processingIdsRef = useRef<Set<number>>(new Set());

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
            status: QuestionStatus | ""
        ) => {
            const requestId = ++listRequestId.current;
            setListLoading(true);
            setListError(false);

            try {
                const data = await fetchQuestions({
                    page: targetPage,
                    size: targetSize,
                    keyword: keyword || undefined,
                    status: status || undefined,
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

    // URLのkeywordが外部要因(戻る/進む等)で変わったら入力欄に反映する
    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setKeywordInput(queryState.keyword);
    }, [queryState.keyword]);

    // キーワード入力をデバウンスしてURLへ反映する(1ページ目に戻す)
    useEffect(() => {
        const timer = setTimeout(() => {
            const trimmed = keywordInput.trim();
            if (trimmed !== queryState.keyword) {
                setQueryState({ keyword: trimmed, page: "1" });
            }
        }, KEYWORD_DEBOUNCE_MS);

        return () => clearTimeout(timer);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [keywordInput]);

    // 検索条件・ページが変わったら選択状態をリセットする
    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setSelectedIds(new Set());
    }, [queryState.keyword, statusFilter, conceptFilter, page]);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        loadList(page, size, queryState.keyword, statusFilter);
    }, [loadList, page, size, queryState.keyword, statusFilter]);

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
            await loadList(page, size, queryState.keyword, statusFilter);
            showToast("質問を削除しました。");
            setDeleteTarget(null);
        } catch (error) {
            console.error(error);
            showToast("質問の削除に失敗しました。", "error");
        } finally {
            setDeleting(false);
        }
    };

    const startReview = (question: Question, action: ReviewAction) => {
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
                const updated = await reviewQuestion(question.id, { action });
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
                        ? "質問を承認しました。"
                        : "質問を却下しました。"
                );
            } catch (error) {
                console.error(error);
                setReviewStatus((prev) => {
                    const next = new Map(prev);
                    next.set(question.id, { action, state: "error" });
                    return next;
                });
                showToast("処理に失敗しました。", "error");
            } finally {
                reviewingIdsRef.current.delete(question.id);
            }
        })();
    };

    const handleConfirmBulkAction = async () => {
        if (!bulkAction || bulkAction === "extract" || selectedIds.size === 0) {
            return;
        }

        setBulkProcessing(true);
        const ids = Array.from(selectedIds);

        try {
            if (bulkAction === "delete") {
                const result = await bulkDeleteQuestions(ids);
                showToast(`${result.deleted_count}件を削除しました。`);
            } else {
                const result = await bulkReviewQuestions(
                    ids,
                    bulkAction === "approve" ? "APPROVE" : "REJECT"
                );
                showToast(
                    `${result.questions.length}件を${bulkAction === "approve" ? "承認" : "却下"}しました。`
                );
            }

            setSelectedIds(new Set());
            setBulkAction(null);
            await loadList(page, size, queryState.keyword, statusFilter);
        } catch (error) {
            console.error(error);
            showToast("一括処理に失敗しました。", "error");
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

    const handlePageChange = (nextPage: number) =>
        setQueryState({ page: String(nextPage) });
    const handleSizeChange = (nextSize: number) =>
        setQueryState({ size: String(nextSize), page: "1" });

    return (
        <main className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-gray-900">
                    質問管理
                </h1>

                <div className="flex items-center gap-2">
                    <Link
                        href="/admin/questions/upload"
                        className={buttonClassName("secondary")}
                    >
                        JSONLアップロード
                    </Link>

                    <Link
                        href="/admin/questions/new"
                        className={buttonClassName("primary")}
                    >
                        新規登録
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
                        関連度検索
                    </button>

                    <button
                        type="button"
                        className={modeButtonClassName(mode === "keyword")}
                        onClick={() => setMode("keyword")}
                    >
                        キーワード検索
                    </button>
                </div>

                {mode === "keyword" && (
                    <>
                        <div className="w-56">
                            <SelectField
                                id="status-filter"
                                label="ステータスで絞り込み"
                                value={statusFilter}
                                onChange={(e) =>
                                    setQueryState({
                                        status: e.target.value,
                                        page: "1",
                                    })
                                }
                                options={[
                                    { value: "", label: "すべて" },
                                    { value: "UNREVIEWED", label: "未レビュー" },
                                    { value: "APPROVED", label: "承認済み" },
                                    { value: "REJECTED", label: "却下" },
                                ]}
                            />
                        </div>

                        <div className="w-56">
                            <SelectField
                                id="concept-filter"
                                label="Concept状態で絞り込み"
                                value={conceptFilter}
                                onChange={(e) =>
                                    setQueryState({
                                        conceptFilter: e.target.value,
                                    })
                                }
                                options={[
                                    { value: "", label: "すべて" },
                                    { value: "extracted", label: "抽出済み" },
                                    { value: "unextracted", label: "未抽出" },
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
                        placeholder="質問を入力すると意味が近い質問を検索します"
                        className={inputClassName}
                    />

                    <Button
                        type="submit"
                        disabled={similarityLoading || !similarityInput.trim()}
                        className="shrink-0"
                    >
                        検索
                    </Button>
                </form>
            ) : (
                <input
                    type="text"
                    value={keywordInput}
                    onChange={(e) => setKeywordInput(e.target.value)}
                    placeholder="キーワードで質問・回答を絞り込み"
                    className={inputClassName}
                />
            )}

            {showSimilarityView ? (
                <>
                    {similarityLoading && <LoadingState label="検索中..." />}

                    {!similarityLoading && similarityError && (
                        <StatusMessage
                            variant="error"
                            message="検索に失敗しました。"
                            onRetry={() => runSimilaritySearch(similarityInput)}
                        />
                    )}

                    {!similarityLoading &&
                        !similarityError &&
                        similarityResults.length === 0 && (
                            <StatusMessage message="関連する質問が見つかりませんでした。" />
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
                                                    関連度{" "}
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
                            message="質問一覧を取得できませんでした。"
                            onRetry={() =>
                                loadList(page, size, queryState.keyword, statusFilter)
                            }
                        />
                    )}

                    {!listLoading && !listError && listItems.length === 0 && (
                        <StatusMessage message="登録されている質問がありません。" />
                    )}

                    {!listLoading &&
                        !listError &&
                        listItems.length > 0 &&
                        visibleItems.length === 0 && (
                            <StatusMessage message="Concept状態の条件に一致する質問がこのページにはありません。" />
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
                                        ? `${selectedIds.size}件選択中`
                                        : "全選択"}
                                </label>

                                {selectedIds.size > 0 && (
                                    <div className="ml-auto flex flex-wrap gap-2">
                                        <Button
                                            variant="secondary"
                                            onClick={() => setBulkAction("approve")}
                                        >
                                            一括承認
                                        </Button>
                                        <Button
                                            variant="secondary"
                                            onClick={() => setBulkAction("reject")}
                                        >
                                            一括却下
                                        </Button>
                                        <Button
                                            variant="secondary"
                                            onClick={() => setBulkAction("extract")}
                                        >
                                            Concept抽出
                                        </Button>
                                        <Button
                                            variant="danger"
                                            onClick={() => setBulkAction("delete")}
                                        >
                                            一括削除
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
                                                    aria-label={`${question.question}を選択`}
                                                />

                                                <div className="flex min-w-0 flex-1 flex-col gap-2">
                                                    <div className="flex flex-wrap items-center gap-2">
                                                        <span
                                                            className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE_CLASSES[question.status]}`}
                                                        >
                                                            {STATUS_LABELS[question.status]}
                                                        </span>

                                                        {question.source === "RAG_RESULT" && (
                                                            <span className="shrink-0 rounded-full bg-purple-50 px-2 py-0.5 text-xs font-medium text-purple-700">
                                                                RAG生成
                                                            </span>
                                                        )}

                                                        <span
                                                            className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                                                                hasConcepts
                                                                    ? "bg-blue-50 text-blue-700"
                                                                    : "bg-gray-100 text-gray-500"
                                                            }`}
                                                        >
                                                            {hasConcepts
                                                                ? `概念抽出済み(${question.concepts.length})`
                                                                : "概念未抽出"}
                                                        </span>

                                                        {extraction === "processing" && (
                                                            <span className="shrink-0 animate-pulse rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                                                                Concept抽出: 処理中
                                                            </span>
                                                        )}

                                                        {extraction === "done" && (
                                                            <span className="shrink-0 rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
                                                                Concept抽出: 完了
                                                            </span>
                                                        )}

                                                        {extraction === "error" && (
                                                            <span className="shrink-0 rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
                                                                Concept抽出: 失敗
                                                            </span>
                                                        )}

                                                        {review?.state === "processing" && (
                                                            <span className="shrink-0 animate-pulse rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                                                                {review.action === "APPROVE"
                                                                    ? "承認中"
                                                                    : "却下中"}
                                                            </span>
                                                        )}

                                                        {review?.state === "error" && (
                                                            <span className="shrink-0 rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
                                                                {review.action === "APPROVE"
                                                                    ? "承認に失敗"
                                                                    : "却下に失敗"}
                                                            </span>
                                                        )}
                                                    </div>

                                                    <span className="font-medium text-gray-900">
                                                        {question.question}
                                                    </span>

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
                                                                承認
                                                            </Button>
                                                        )}

                                                        {question.status !== "REJECTED" && (
                                                            <Button
                                                                variant="secondary"
                                                                disabled={review?.state === "processing"}
                                                                onClick={() =>
                                                                    startReview(question, "REJECT")
                                                                }
                                                            >
                                                                却下
                                                            </Button>
                                                        )}

                                                        <Link
                                                            href={`/admin/questions/${question.id}/reviews`}
                                                            className={buttonClassName("secondary")}
                                                        >
                                                            履歴
                                                        </Link>

                                                        <Link
                                                            href={`/admin/questions/${question.id}/edit`}
                                                            className={buttonClassName("secondary")}
                                                        >
                                                            編集
                                                        </Link>

                                                        <Button
                                                            variant="secondary"
                                                            disabled={extraction === "processing"}
                                                            onClick={() =>
                                                                startConceptExtraction([question.id])
                                                            }
                                                        >
                                                            Concept抽出
                                                        </Button>

                                                        <Button
                                                            variant="danger"
                                                            onClick={() => setDeleteTarget(question)}
                                                        >
                                                            削除
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
                title="質問を削除しますか？"
                description={deleteTarget?.question}
                confirming={deleting}
                onConfirm={handleConfirmDelete}
                onCancel={() => setDeleteTarget(null)}
            />

            <ConfirmDialog
                open={bulkAction !== null}
                title={bulkAction ? BULK_ACTION_LABELS[bulkAction].title : ""}
                description={`${selectedIds.size}件が対象です。`}
                confirmLabel={bulkAction ? BULK_ACTION_LABELS[bulkAction].confirmLabel : undefined}
                confirming={bulkAction === "extract" ? false : bulkProcessing}
                onConfirm={() =>
                    bulkAction === "extract"
                        ? startConceptExtraction(Array.from(selectedIds))
                        : handleConfirmBulkAction()
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
