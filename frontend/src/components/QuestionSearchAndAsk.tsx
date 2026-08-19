"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, ReactNode, useCallback, useRef, useState } from "react";
import { ApiError, askAi, fetchQuestionByExactText, searchQuestions } from "@/lib/api";
import { SimilarQuestion } from "@/types/question";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import LoadingState from "@/components/ui/LoadingState";
import StatusMessage from "@/components/ui/StatusMessage";
import MarkdownContent from "@/components/ui/MarkdownContent";
import { showToast } from "@/components/ui/Toast";
import { useLanguage } from "@/lib/i18n/LanguageContext";

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

/**
 * 質問を関連度検索し、結果を表示したうえで「目的の質問はありませんか？」
 * からRAGモードのAI回答生成へ進める共有フロー。トップページ(検索前は
 * children で質問一覧をフォールバック表示)と質問詳細ページ(children なし)
 * の両方から使われる。
 */
export default function QuestionSearchAndAsk({
    children,
}: QuestionSearchAndAskProps) {
    const router = useRouter();
    const { language, t } = useLanguage();
    const [query, setQuery] = useState("");
    const [searched, setSearched] = useState(false);
    const [results, setResults] = useState<SimilarQuestion[]>([]);
    const [searchLoading, setSearchLoading] = useState(false);
    const [searchError, setSearchError] = useState(false);
    const searchRequestId = useRef(0);

    const [ragAnswer, setRagAnswer] = useState<string | null>(null);
    const [ragLoading, setRagLoading] = useState(false);
    const ragRequestId = useRef(0);

    const runSearch = useCallback(async (rawQuery: string) => {
        const trimmed = rawQuery.trim();

        if (!trimmed) {
            return;
        }

        const requestId = ++searchRequestId.current;
        setSearchLoading(true);
        setSearchError(false);

        // 完全一致するQAが既にあれば、検索結果を経由せずその個別ページへ直接遷移する。
        let exactMatchId: number | null = null;
        try {
            exactMatchId = (await fetchQuestionByExactText(trimmed)).id;
        } catch (error) {
            if (!(error instanceof ApiError && error.status === 404)) {
                console.error(error);
            }
        }

        if (requestId !== searchRequestId.current) {
            return;
        }

        if (exactMatchId !== null) {
            router.push(`/questions/${exactMatchId}?matched=exact`);
            return;
        }

        setSearched(true);
        setRagAnswer(null);
        ragRequestId.current += 1;

        try {
            const data = await searchQuestions({
                query: trimmed,
                limit: SIMILARITY_LIMIT,
            });

            if (requestId !== searchRequestId.current) {
                return;
            }

            setResults(data);
        } catch (error) {
            if (requestId !== searchRequestId.current) {
                return;
            }

            console.error(error);
            setSearchError(true);
        } finally {
            if (requestId === searchRequestId.current) {
                setSearchLoading(false);
            }
        }
    }, [router]);

    const runRag = useCallback(async (rawQuery: string, searchResults: SimilarQuestion[]) => {
        const trimmed = rawQuery.trim();

        if (!trimmed) {
            return;
        }

        const requestId = ++ragRequestId.current;
        setRagLoading(true);
        setRagAnswer(null);

        try {
            const retrievedQuestionIds = searchResults.map((result) => result.id);
            const result = await askAi(
                trimmed,
                "RAG",
                retrievedQuestionIds.length > 0 ? retrievedQuestionIds : undefined
            );

            if (requestId !== ragRequestId.current) {
                return;
            }

            setRagAnswer(result.answer);
        } catch (error) {
            if (requestId !== ragRequestId.current) {
                return;
            }

            console.error(error);
            showToast(t("questionSearch.askFailed"), "error");
        } finally {
            if (requestId === ragRequestId.current) {
                setRagLoading(false);
            }
        }
    }, [t]);

    function handleSubmit(e: FormEvent<HTMLFormElement>) {
        e.preventDefault();
        runSearch(query);
    }

    const trimmedLength = query.trim().length;
    const belowMinLength = trimmedLength > 0 && trimmedLength < QUESTION_MIN_LENGTH;

    return (
        <div className="flex flex-col gap-4">
            <form onSubmit={handleSubmit} className="flex flex-col gap-1">
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
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

            {language === "en" && (
                <p className="text-xs text-gray-500">
                    Please write your question in Japanese.
                    <br />
                    English questions are not supported yet.
                </p>
            )}

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
                                    <Link key={result.id} href={`/questions/${result.id}`}>
                                        <Card
                                            className={`transition-colors hover:border-blue-300 hover:bg-blue-50/50 ${topResultRingClassName(isTopResult, percent)}`}
                                            style={{
                                                backgroundColor: topResultBackgroundColor(
                                                    isTopResult,
                                                    percent
                                                ),
                                            }}
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
                                        </Card>
                                    </Link>
                                );
                            })}
                        </div>
                    )}

                    {ragLoading && <LoadingState label={t("questionSearch.generating")} />}

                    {!ragLoading && ragAnswer && (
                        <Card>
                            <MarkdownContent content={ragAnswer} variant="full" />
                        </Card>
                    )}
                </>
            )}
        </div>
    );
}
