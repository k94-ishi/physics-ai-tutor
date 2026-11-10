"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { fetchQuestions, searchQuestions } from "@/lib/api";
import {
    AiVerdictFilter,
    Question,
    QuestionSort,
    QuestionStatus,
    SimilarQuestion,
} from "@/types/question";
import { useQueryState } from "@/lib/hooks/useQueryState";
import { parseIdSearch } from "@/lib/questionIds";
import { ConceptFilter, QueueMode } from "@/components/admin/AdminQueueFilters";
import { useLatestRequest } from "@/lib/hooks/useLatestRequest";

function fromUrl<T extends string>(
    value: string,
    allowed: readonly T[],
): T | "" {
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
const SIMILARITY_LIMIT = 10;
const KEYWORD_DEBOUNCE_MS = 300;
const ADMIN_QUERY_DEFAULTS = {
    page: "1",
    size: "30",
    keyword: "",
    ids: "",
    status: "",
    conceptFilter: "",
    // タグで絞り込む([41])。サーバー側で絞るので件数とページ送りが正しい。
    concept: "",
    sort: "",
    aiVerdict: "",
};

/** List state of the admin queue: URL filters, loading, searches, paging ([63]). */
export function useAdminQueueList() {
    const [mode, setMode] = useState<QueueMode>("keyword");

    const [queryState, setQueryState] = useQueryState(ADMIN_QUERY_DEFAULTS);
    const page = Number(queryState.page);
    const size = Number(queryState.size);
    const statusFilter = fromUrl(queryState.status, STATUS_VALUES);
    const conceptFilter = fromUrl(
        queryState.conceptFilter,
        CONCEPT_FILTER_VALUES,
    );
    const sortOption = fromUrl(queryState.sort, SORT_VALUES);
    const aiVerdictFilter = fromUrl(queryState.aiVerdict, AI_VERDICT_VALUES);
    const [keywordInput, setKeywordInput] = useState(queryState.keyword);
    const [listItems, setListItems] = useState<Question[]>([]);
    const [listTotal, setListTotal] = useState(0);
    const [listLoading, setListLoading] = useState(true);
    const [listError, setListError] = useState(false);
    const listRequestId = useLatestRequest();

    const [similarityInput, setSimilarityInput] = useState("");
    const [similaritySearched, setSimilaritySearched] = useState(false);
    const [similarityResults, setSimilarityResults] = useState<
        SimilarQuestion[]
    >([]);
    const [similarityLoading, setSimilarityLoading] = useState(false);
    const [similarityError, setSimilarityError] = useState(false);
    const similarityRequestId = useLatestRequest();

    const loadList = useCallback(
        async (
            targetPage: number,
            targetSize: number,
            keyword: string,
            status: QuestionStatus | "",
            sort: QuestionSort | "" = "",
            aiVerdict: AiVerdictFilter | "" = "",
            ids: string = "",
            concept: string = "",
        ) => {
            const isCurrent = listRequestId.begin();
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
                    concept: concept || undefined,
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
        [listRequestId],
    );

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setKeywordInput(
            queryState.ids ? `#${queryState.ids}` : queryState.keyword,
        );
    }, [queryState.keyword, queryState.ids]);

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

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        loadList(
            page,
            size,
            queryState.keyword,
            statusFilter,
            sortOption,
            aiVerdictFilter,
            queryState.ids,
            queryState.concept,
        );
    }, [
        loadList,
        page,
        size,
        queryState.keyword,
        queryState.ids,
        queryState.concept,
        statusFilter,
        sortOption,
        aiVerdictFilter,
        listRequestId,
    ]);

    const runSimilaritySearch = useCallback(async (query: string) => {
        const trimmed = query.trim();

        if (!trimmed) {
            return;
        }

        const isCurrent = similarityRequestId.begin();
        setSimilaritySearched(true);
        setSimilarityLoading(true);
        setSimilarityError(false);

        try {
            const results = await searchQuestions({
                query: trimmed,
                limit: SIMILARITY_LIMIT,
            });

            if (!isCurrent()) {
                return;
            }

            setSimilarityResults(results);
        } catch (error) {
            if (!isCurrent()) {
                return;
            }

            console.error(error);
            setSimilarityError(true);
        } finally {
            if (isCurrent()) {
                setSimilarityLoading(false);
            }
        }
    }, [similarityRequestId]);

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

    const handlePageChange = (nextPage: number) =>
        setQueryState({ page: String(nextPage) });
    const handleSizeChange = (nextSize: number) =>
        setQueryState({ size: String(nextSize), page: "1" });

    return {
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
        setListItems,
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
    };
}

export type AdminQueueList = ReturnType<typeof useAdminQueueList>;
