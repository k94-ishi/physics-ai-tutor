"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { fetchQuestions } from "@/lib/api";
import { Question } from "@/types/question";
import QuestionCard from "@/components/ui/QuestionCard";
import LoadingState from "@/components/ui/LoadingState";
import StatusMessage from "@/components/ui/StatusMessage";
import Pagination from "@/components/ui/Pagination";
import ReferencedQuestions from "@/components/ui/ReferencedQuestions";
import QuestionSearchAndAsk from "@/components/QuestionSearchAndAsk";
import QuestionPreviewModal, {
    PreviewQuestion,
} from "@/components/ui/QuestionPreviewModal";
import MeaningChooser from "@/components/ui/MeaningChooser";
import { ConceptSearchItem } from "@/types/concept";
import { useQueryState } from "@/lib/hooks/useQueryState";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { useLatestRequest } from "@/lib/hooks/useLatestRequest";

type Mode = "similarity" | "keyword";

const KEYWORD_DEBOUNCE_MS = 300;

const LIST_QUERY_DEFAULTS = {
    page: "1",
    size: "30",
    keyword: "",
    // Tag chip filter ([41]); empty means no filter.
    concept: "",
    // Exact tag sense filter ([55]); `concept` holds the label for the banner.
    conceptId: "",
    // Vector search ([49]); QuestionSearchAndAsk owns it, it only picks the first tab here.
    similar: "",
};

function modeButtonClassName(active: boolean): string {
    return `rounded-md px-4 py-2 text-sm font-medium transition-colors ${
        active
            ? "bg-blue-600 text-white"
            : "border border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
    }`;
}

const inputClassName =
    "w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

function QuestionListInner() {
    const { language, resolved, t } = useLanguage();

    // List state (page, size, keyword) lives in the URL.
    const [queryState, setQueryState] = useQueryState(LIST_QUERY_DEFAULTS);
    // Open the tab the URL implies, so a shared link lands in the right place.
    const [mode, setMode] = useState<Mode>(() =>
        queryState.keyword !== "" && queryState.similar === ""
            ? "keyword"
            : "similarity"
    );
    const page = Number(queryState.page);
    const size = Number(queryState.size);
    const [keywordInput, setKeywordInput] = useState(queryState.keyword);
    const [searchQuestion, setSearchQuestion] = useState(true);
    const [searchAnswer, setSearchAnswer] = useState(true);
    const [listItems, setListItems] = useState<Question[]>([]);
    const [listTotal, setListTotal] = useState(0);
    const [listLoading, setListLoading] = useState(true);
    const [listError, setListError] = useState(false);
    const listRequestId = useLatestRequest();
    const [preview, setPreview] = useState<PreviewQuestion | null>(null);

    const loadList = useCallback(
        async (
            targetPage: number,
            targetSize: number,
            keyword: string,
            targetSearchQuestion: boolean,
            targetSearchAnswer: boolean,
            concept: string,
            conceptId: string
        ) => {
            const isCurrent = listRequestId.begin();
            setListLoading(true);
            setListError(false);

            try {
                const data = await fetchQuestions({
                    page: targetPage,
                    size: targetSize,
                    keyword: keyword || undefined,
                    status: "APPROVED",
                    searchQuestion: targetSearchQuestion,
                    searchAnswer: targetSearchAnswer,
                    lang: language,
                    // A chosen sense is exact; a bare word covers all its senses.
                    concept: conceptId ? undefined : concept || undefined,
                    conceptId: conceptId ? Number(conceptId) : undefined,
                });

                if (!isCurrent()) {
                    return;
                }

                setListItems(data.items);
                setListTotal(data.total);
            } catch (error) {
                if (!isCurrent()) {
                    return;
                }

                console.error(error);
                setListError(true);
            } finally {
                if (isCurrent()) {
                    setListLoading(false);
                }
            }
        },
        [language, listRequestId]
    );

    // Reflect URL keyword changes (back/forward) in the input.
    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setKeywordInput(queryState.keyword);
    }, [queryState.keyword]);

    // Debounce keyword typing into the URL and go back to page 1.
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

    // Fetch the list whenever its inputs settle, including the first load.
    useEffect(() => {
        // Wait for the language, or the list loads once in ja and again ([53]).
        if (!resolved) {
            return;
        }
        // eslint-disable-next-line react-hooks/set-state-in-effect
        loadList(
            page,
            size,
            queryState.keyword,
            searchQuestion,
            searchAnswer,
            queryState.concept,
            queryState.conceptId
        );
    }, [
        resolved,
        loadList,
        page,
        size,
        queryState.keyword,
        searchQuestion,
        searchAnswer,
        queryState.concept,
        queryState.conceptId,
        listRequestId,
    ]);

    const handlePageChange = (nextPage: number) =>
        setQueryState({ page: String(nextPage) });
    const handleSizeChange = (nextSize: number) =>
        setQueryState({ size: String(nextSize), page: "1" });

    // Keep at least one of question/answer searched, or the filter breaks.
    const toggleSearchQuestion = () => {
        setSearchQuestion((prev) => (prev && !searchAnswer ? prev : !prev));
    };
    const toggleSearchAnswer = () => {
        setSearchAnswer((prev) => (prev && !searchQuestion ? prev : !prev));
    };

    // Both tabs share this list: the AI tab before a search, the keyword tab always.
    const conceptBanner = queryState.concept ? (
        <div className="flex flex-wrap items-center gap-3 rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-800">
            <span>
                {t("concepts.filterBanner", { concept: queryState.concept })}
            </span>
            <button
                type="button"
                onClick={() =>
                    setQueryState({ concept: "", conceptId: "", page: "1" })
                }
                className="cursor-pointer font-medium underline underline-offset-2"
            >
                {t("concepts.clearFilter")}
            </button>
        </div>
    ) : null;

    const chooseSense = (item: ConceptSearchItem) =>
        setQueryState({
            concept: item.label,
            conceptId: String(item.id),
            page: "1",
        });

    const browseList = (
        <>
            {conceptBanner}

            {queryState.concept && !queryState.conceptId && (
                <MeaningChooser word={queryState.concept} onSelect={chooseSense} />
            )}

            {listLoading && <LoadingState />}

            {!listLoading && listError && (
                <StatusMessage
                    variant="error"
                    message={t("questionList.fetchFailed")}
                    onRetry={() =>
                        loadList(
                            page,
                            size,
                            queryState.keyword,
                            searchQuestion,
                            searchAnswer,
                            queryState.concept,
                            queryState.conceptId
                        )
                    }
                />
            )}

            {!listLoading && !listError && listItems.length === 0 && (
                <StatusMessage
                    message={
                        queryState.concept
                            ? t("concepts.noMatch", { concept: queryState.concept })
                            : t("questionList.empty")
                    }
                />
            )}

            {!listLoading && !listError && listItems.length > 0 && (
                <>
                    <Pagination
                        page={page}
                        size={size}
                        total={listTotal}
                        onPageChange={handlePageChange}
                        onSizeChange={handleSizeChange}
                    />

                    <div className="flex flex-col gap-3">
                        {listItems.map((question) => (
                            <QuestionCard
                                key={question.id}
                                question={question}
                                onOpen={() => setPreview(question)}
                            >
                                <ReferencedQuestions
                                items={question.retrieved_questions}
                                />
                            </QuestionCard>
                        ))}
                    </div>

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
    );

    return (
        <div className="flex flex-col gap-4">
            <div className="flex gap-2">
                <button
                    type="button"
                    className={modeButtonClassName(mode === "similarity")}
                    onClick={() => setMode("similarity")}
                >
                    {t("questionList.modeAi")}
                </button>

                <button
                    type="button"
                    className={modeButtonClassName(mode === "keyword")}
                    onClick={() => setMode("keyword")}
                >
                    {t("common.keywordSearch")}
                </button>
            </div>

            <QuestionPreviewModal
                question={preview}
                onClose={() => setPreview(null)}
            />

            {mode === "similarity" ? (
                <QuestionSearchAndAsk>{browseList}</QuestionSearchAndAsk>
            ) : (
                <>
                    <input
                        type="text"
                        value={keywordInput}
                        onChange={(e) => setKeywordInput(e.target.value)}
                        placeholder={t("questionList.keywordPlaceholder")}
                        className={inputClassName}
                    />

                    <div className="flex gap-4 text-sm text-gray-600">
                        <label className="flex items-center gap-2">
                            <input
                                type="checkbox"
                                checked={searchQuestion}
                                onChange={toggleSearchQuestion}
                            />
                            {t("questionList.searchInQuestion")}
                        </label>

                        <label className="flex items-center gap-2">
                            <input
                                type="checkbox"
                                checked={searchAnswer}
                                onChange={toggleSearchAnswer}
                            />
                            {t("questionList.searchInAnswer")}
                        </label>
                    </div>

                    {browseList}
                </>
            )}
        </div>
    );
}

export default function QuestionList() {
    return (
        <Suspense fallback={<LoadingState />}>
            <QuestionListInner />
        </Suspense>
    );
}
