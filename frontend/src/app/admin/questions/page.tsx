"use client";

import { Suspense } from "react";
import Link from "next/link";
import Card from "@/components/ui/Card";
import Button, { buttonClassName } from "@/components/ui/Button";
import LoadingState from "@/components/ui/LoadingState";
import StatusMessage from "@/components/ui/StatusMessage";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import ReviewReasonDialog from "@/components/ui/ReviewReasonDialog";
import Pagination from "@/components/ui/Pagination";
import MarkdownContent from "@/components/ui/MarkdownContent";
import { BulkAction, useAdminQueueActions } from "@/app/admin/questions/useAdminQueueActions";
import { useAdminQueueList } from "@/app/admin/questions/useAdminQueueList";
import AdminQueueFilters from "@/components/admin/AdminQueueFilters";
import AdminQuestionCard from "@/components/admin/AdminQuestionCard";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { TranslationKey } from "@/lib/i18n/translations";


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


function similarityPercent(distance: number): number {
    return Math.max(0, Math.round((1 - distance) * 100));
}


function AdminQuestionsPageInner() {
    const { t } = useLanguage();
    const list = useAdminQueueList();
    const {
        mode,
        setMode,
        queryState,
        setQueryState,
        page,
        size,
        statusFilter,
        conceptFilter,
        sortOption,
        aiVerdictFilter,
        keywordInput,
        setKeywordInput,
        listItems,
        listTotal,
        listLoading,
        listError,
        similarityInput,
        setSimilarityInput,
        similarityResults,
        similarityLoading,
        similarityError,
        loadList,
        runSimilaritySearch,
        handleSimilaritySubmit,
        showSimilarityView,
        visibleItems,
        handlePageChange,
        handleSizeChange,
    } = list;
    const {
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
    } = useAdminQueueActions(list);
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

            <AdminQueueFilters
                mode={mode}
                onModeChange={setMode}
                status={statusFilter}
                conceptFilter={conceptFilter}
                sort={sortOption}
                aiVerdict={aiVerdictFilter}
                onQueryChange={setQueryState}
                keywordInput={keywordInput}
                onKeywordInput={setKeywordInput}
                similarityInput={similarityInput}
                onSimilarityInput={setSimilarityInput}
                similarityLoading={similarityLoading}
                onSimilaritySubmit={handleSimilaritySubmit}
            />

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
                    {queryState.concept && (
                        <div className="flex flex-wrap items-center gap-3 rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-800">
                            <span>
                                {t("concepts.filterBanner", {
                                    concept: queryState.concept,
                                })}
                            </span>
                            <button
                                type="button"
                                onClick={() => setQueryState({ concept: "", page: "1" })}
                                className="cursor-pointer font-medium underline underline-offset-2"
                            >
                                {t("concepts.clearFilter")}
                            </button>
                        </div>
                    )}

                    {listLoading && <LoadingState />}

                    {!listLoading && listError && (
                        <StatusMessage
                            variant="error"
                            message={t("admin.fetchFailed")}
                            onRetry={() =>
                                loadList(page, size, queryState.keyword, statusFilter, sortOption, aiVerdictFilter, queryState.ids, queryState.concept)
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
                                    const isSelected = selectedIds.has(question.id);
                                    const extraction = extractionStatus.get(question.id);
                                    const review = reviewStatus.get(question.id);

                                    return (
                                        <li key={question.id}>
                                            <AdminQuestionCard
                                                question={question}
                                                isSelected={isSelected}
                                                extraction={extraction}
                                                review={review}
                                                aiReviewing={aiReviewingIds.has(question.id)}
                                                aiBusy={aiRun.running || aiRun.starting}
                                                activeConcept={queryState.concept}
                                                onToggleSelected={() => toggleSelected(question.id)}
                                                onFilterConcept={(concept) =>
                                                    setQueryState({ concept, page: "1" })
                                                }
                                                onApprove={() => startReview(question, "APPROVE")}
                                                onReject={() => setRejectTarget(question)}
                                                onAiReview={() => startAiReviewSelected([question.id])}
                                                onExtract={() => startConceptExtraction([question.id])}
                                                onDelete={() => setDeleteTarget(question)}
                                            />
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
