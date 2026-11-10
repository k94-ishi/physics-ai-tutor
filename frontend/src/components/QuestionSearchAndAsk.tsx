"use client";

import { useRouter } from "next/navigation";
import {
    FormEvent,
    ReactNode,
    useCallback,
    useEffect,
    useRef,
    useState,
} from "react";
import { ApiError, askAi, fetchQuestionByExactText, searchQuestions } from "@/lib/api";
import { ContentLanguage, SimilarQuestion } from "@/types/question";
import { AskAiResponse } from "@/types/ai";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import LoadingState from "@/components/ui/LoadingState";
import StatusMessage from "@/components/ui/StatusMessage";
import MarkdownContent from "@/components/ui/MarkdownContent";
import QuestionPreviewModal, {
    PreviewQuestion,
} from "@/components/ui/QuestionPreviewModal";
import { showToast } from "@/components/ui/Toast";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { useQueryState } from "@/lib/hooks/useQueryState";
import { useLatestRequest } from "@/lib/hooks/useLatestRequest";

const SIMILARITY_LIMIT = 10;
const QUESTION_MIN_LENGTH = 5;
const QUESTION_MAX_LENGTH = 200;
const HIGH_SIMILARITY_THRESHOLD = 95;
const MEDIUM_SIMILARITY_THRESHOLD = 90;

const inputClassName =
    "w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

function similarityPercent(distance: number): number {
    return Math.max(0, Math.round((1 - distance) * 100));
}

// Card.tsx bakes in a fixed "border-gray-200 bg-white" that sorts after
// plain color utilities in Tailwind's generated stylesheet, so a same-
// property override (border-color/background-color) from a later className
// silently loses the cascade. `ring` (box-shadow) and an inline
// backgroundColor sidestep that instead of fighting it.
function topResultRingClassName(isTopResult: boolean, percent: number): string {
    if (!isTopResult) {
        return "";
    }
    if (percent >= HIGH_SIMILARITY_THRESHOLD) {
        return "ring-2 ring-green-400";
    }
    if (percent >= MEDIUM_SIMILARITY_THRESHOLD) {
        return "ring-2 ring-blue-300";
    }
    return "";
}

function topResultBackgroundColor(
    isTopResult: boolean,
    percent: number
): string | undefined {
    if (!isTopResult) {
        return undefined;
    }
    if (percent >= HIGH_SIMILARITY_THRESHOLD) {
        return "#f0fdf4";
    }
    if (percent >= MEDIUM_SIMILARITY_THRESHOLD) {
        return "#eff6ff";
    }
    return undefined;
}

function topResultBadgeClassName(isTopResult: boolean, percent: number): string {
    if (isTopResult && percent >= HIGH_SIMILARITY_THRESHOLD) {
        return "bg-green-50 text-green-700";
    }
    return "bg-blue-50 text-blue-700";
}

type QuestionSearchAndAskProps = {
    children?: ReactNode;
};

/** Similarity search with a path on to a RAG answer, shared by the home and question pages. */
// URL key for a shared vector search ([49]); `similar`, not `q` (owner, 2026-11-02).
const SEARCH_QUERY_DEFAULTS = { similar: "" };

export default function QuestionSearchAndAsk({
    children,
}: QuestionSearchAndAskProps) {
    const router = useRouter();
    const { language, resolved: languageResolved, t } = useLanguage();
    const [queryState, setQueryState] = useQueryState(SEARCH_QUERY_DEFAULTS);
    const [query, setQuery] = useState(queryState.similar);
    const [searched, setSearched] = useState(false);
    const [results, setResults] = useState<SimilarQuestion[]>([]);
    const [searchLoading, setSearchLoading] = useState(false);
    const [searchError, setSearchError] = useState(false);
    const searchRequestId = useLatestRequest();

    const [ragAnswer, setRagAnswer] = useState<AskAiResponse | null>(null);
    const [ragLoading, setRagLoading] = useState(false);
    const ragRequestId = useLatestRequest();
    // Similarity results open in the preview instead of leaving the page ([56]).
    const [preview, setPreview] = useState<PreviewQuestion | null>(null);
    const contentLanguage = language as ContentLanguage;

    const runSearch = useCallback(async (
        rawQuery: string,
        options?: { skipExactRedirect?: boolean }
    ) => {
        const trimmed = rawQuery.trim();

        if (!trimmed) {
            return;
        }

        const isCurrent = searchRequestId.begin();
        setSearchLoading(true);
        setSearchError(false);

        // Go straight to an exact match, except when restoring from the URL, so back never bounces forward.
        if (!options?.skipExactRedirect) {
            let exactMatchId: number | null = null;
            try {
                exactMatchId = (
                    await fetchQuestionByExactText(trimmed, contentLanguage)
                ).id;
            } catch (error) {
                if (!(error instanceof ApiError && error.status === 404)) {
                    console.error(error);
                }
            }

            if (!isCurrent()) {
                return;
            }

            if (exactMatchId !== null) {
                router.push(`/questions/${exactMatchId}?matched=exact`);
                return;
            }
        }

        setSearched(true);
        setRagAnswer(null);
        ragRequestId.cancel();

        try {
            const data = await searchQuestions({
                query: trimmed,
                limit: SIMILARITY_LIMIT,
                language: contentLanguage,
            });

            if (!isCurrent()) {
                return;
            }

            setResults(data);
        } catch (error) {
            if (!isCurrent()) {
                return;
            }

            console.error(error);
            setSearchError(true);
        } finally {
            if (isCurrent()) {
                setSearchLoading(false);
            }
        }
    }, [router, contentLanguage, ragRequestId, searchRequestId]);

    const runRag = useCallback(async (rawQuery: string, searchResults: SimilarQuestion[]) => {
        const trimmed = rawQuery.trim();

        if (!trimmed) {
            return;
        }

        const isCurrent = ragRequestId.begin();
        setRagLoading(true);
        setRagAnswer(null);

        try {
            const retrievedQuestionIds = searchResults.map((result) => result.id);
            const result = await askAi(trimmed, {
                language: contentLanguage,
                mode: "RAG",
                retrievedQuestionIds:
                    retrievedQuestionIds.length > 0
                        ? retrievedQuestionIds
                        : undefined,
            });

            if (!isCurrent()) {
                return;
            }

            setRagAnswer(result);
        } catch (error) {
            if (!isCurrent()) {
                return;
            }

            console.error(error);
            showToast(t("questionSearch.askFailed"), "error");
        } finally {
            if (isCurrent()) {
                setRagLoading(false);
            }
        }
    }, [t, contentLanguage, ragRequestId]);

    // Restore `?similar=` once per URL and language, re-running on a language switch ([50]).
    const lastExecutedRef = useRef<string | null>(null);

    useEffect(() => {
        // Wait for the language, or the search runs in ja and then again ([50]).
        if (!languageResolved) {
            return;
        }

        const target = queryState.similar.trim();
        if (target === "") {
            // Reset only once the URL is really empty, so a stale render cannot search twice.
            lastExecutedRef.current = null;
            return;
        }

        const executionKey = `${contentLanguage}:${target}`;
        if (lastExecutedRef.current === executionKey) {
            return;
        }

        lastExecutedRef.current = executionKey;
        setQuery(target);
        runSearch(target, { skipExactRedirect: true });
    }, [queryState.similar, contentLanguage, languageResolved, runSearch]);

    function handleQueryChange(value: string) {
        setQuery(value);

        // Clearing the box clears `?similar=`; the only URL write allowed on a keystroke.
        if (value.trim() === "" && queryState.similar !== "") {
            setQueryState({ similar: "" });
        }
    }

    function handleSubmit(e: FormEvent<HTMLFormElement>) {
        e.preventDefault();
        const trimmed = query.trim();

        if (trimmed === "") {
            return;
        }

        lastExecutedRef.current = `${contentLanguage}:${trimmed}`;
        setQueryState({ similar: trimmed });
        runSearch(trimmed);
    }

    const trimmedLength = query.trim().length;
    const belowMinLength = trimmedLength > 0 && trimmedLength < QUESTION_MIN_LENGTH;

    return (
        <div className="flex flex-col gap-4">
            <QuestionPreviewModal
                question={preview}
                onClose={() => setPreview(null)}
            />

            <form onSubmit={handleSubmit} className="flex flex-col gap-1">
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => handleQueryChange(e.target.value)}
                        placeholder={t("questionSearch.placeholder")}
                        maxLength={QUESTION_MAX_LENGTH}
                        className={inputClassName}
                    />

                    <Button
                        type="submit"
                        disabled={searchLoading || trimmedLength < QUESTION_MIN_LENGTH}
                        className="shrink-0"
                    >
                        {t("common.search")}
                    </Button>
                </div>

                <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>
                        {belowMinLength &&
                            t("questionSearch.minLength", {
                                min: QUESTION_MIN_LENGTH,
                            })}
                    </span>
                    <span>
                        {trimmedLength} / {QUESTION_MAX_LENGTH}
                    </span>
                </div>
            </form>

            {!searched && children}

            {searched && (
                <>
                    {!searchLoading && (
                        <div className="flex flex-col items-start gap-2 rounded-md border border-gray-200 bg-gray-50 p-4">
                            <p className="text-sm text-gray-600">
                                {t("questionSearch.askPrompt")}
                            </p>
                            <Button
                                type="button"
                                variant="secondary"
                                disabled={ragLoading || trimmedLength < QUESTION_MIN_LENGTH}
                                onClick={() => runRag(query, results)}
                            >
                                {t("questionSearch.askButton")}
                            </Button>
                        </div>
                    )}

                    {searchLoading && <LoadingState label={t("common.searching")} />}

                    {!searchLoading && searchError && (
                        <StatusMessage
                            variant="error"
                            message={t("common.searchFailed")}
                            onRetry={() => runSearch(query)}
                        />
                    )}

                    {!searchLoading && !searchError && results.length === 0 && (
                        <StatusMessage message={t("questionSearch.noResults")} />
                    )}

                    {!searchLoading && !searchError && results.length > 0 && (
                        <div className="flex flex-col gap-3">
                            {results.map((result, index) => {
                                const percent = similarityPercent(result.distance);
                                const isTopResult = index === 0;

                                return (
                                    <Card
                                        key={result.id}
                                        className={`transition-colors hover:border-blue-300 hover:bg-blue-50/50 ${topResultRingClassName(isTopResult, percent)}`}
                                        style={{
                                            backgroundColor: topResultBackgroundColor(
                                                isTopResult,
                                                percent
                                            ),
                                        }}
                                    >
                                        <button
                                            type="button"
                                            onClick={() => setPreview(result)}
                                            className="flex w-full cursor-pointer flex-col text-left"
                                        >
                                            {isTopResult && percent >= HIGH_SIMILARITY_THRESHOLD && (
                                                <p className="mb-1 text-xs font-medium text-green-700">
                                                    {t("questionSearch.topMatchBanner")}
                                                </p>
                                            )}

                                            <div className="flex items-start justify-between gap-3">
                                                <span className="font-medium text-gray-900">
                                                    {result.question}
                                                </span>

                                                <span
                                                    className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${topResultBadgeClassName(isTopResult, percent)}`}
                                                >
                                                    {t("questionSearch.relevance")} {percent}%
                                                </span>
                                            </div>

                                            <MarkdownContent
                                                content={result.answer}
                                                variant="preview"
                                            />
                                        </button>
                                    </Card>
                                );
                            })}
                        </div>
                    )}

                    {ragLoading && <LoadingState label={t("questionSearch.generating")} />}

                    {!ragLoading && ragAnswer && (
                        <Card className="flex flex-col gap-2">
                            {ragAnswer.cached && (
                                <p className="text-xs text-gray-500">
                                    {t("questionSearch.cachedNotice")}
                                </p>
                            )}

                            <MarkdownContent
                                content={ragAnswer.answer}
                                variant="full"
                            />

                            {ragAnswer.status === "UNREVIEWED" && (
                                <p className="rounded-md bg-yellow-50 px-3 py-2 text-xs text-yellow-700">
                                    {t("questionSearch.answerUnreviewed")}
                                </p>
                            )}
                        </Card>
                    )}
                </>
            )}
        </div>
    );
}
