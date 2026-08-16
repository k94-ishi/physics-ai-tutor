"use client";

import Link from "next/link";
import { FormEvent, ReactNode, useCallback, useRef, useState } from "react";
import { askAi, searchQuestions } from "@/lib/api";
import { SimilarQuestion } from "@/types/question";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import LoadingState from "@/components/ui/LoadingState";
import StatusMessage from "@/components/ui/StatusMessage";
import MarkdownContent from "@/components/ui/MarkdownContent";
import { showToast } from "@/components/ui/Toast";

const SIMILARITY_LIMIT = 10;
const QUESTION_MIN_LENGTH = 5;
const QUESTION_MAX_LENGTH = 200;

const inputClassName =
    "w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

function similarityPercent(distance: number): number {
    return Math.max(0, Math.round((1 - distance) * 100));
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
        setSearched(true);
        setSearchLoading(true);
        setSearchError(false);
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
    }, []);

    const runRag = useCallback(async (rawQuery: string) => {
        const trimmed = rawQuery.trim();

        if (!trimmed) {
            return;
        }

        const requestId = ++ragRequestId.current;
        setRagLoading(true);
        setRagAnswer(null);

        try {
            const result = await askAi(trimmed, "RAG");

            if (requestId !== ragRequestId.current) {
                return;
            }

            setRagAnswer(result.answer);
        } catch (error) {
            if (requestId !== ragRequestId.current) {
                return;
            }

            console.error(error);
            showToast("AIへの質問に失敗しました。", "error");
        } finally {
            if (requestId === ragRequestId.current) {
                setRagLoading(false);
            }
        }
    }, []);

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
                        placeholder="質問を入力すると意味が近い質問を検索します"
                        maxLength={QUESTION_MAX_LENGTH}
                        className={inputClassName}
                    />

                    <Button
                        type="submit"
                        disabled={searchLoading || trimmedLength < QUESTION_MIN_LENGTH}
                        className="shrink-0"
                    >
                        検索
                    </Button>
                </div>

                <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>
                        {belowMinLength && `${QUESTION_MIN_LENGTH}文字以上入力してください`}
                    </span>
                    <span>
                        {trimmedLength} / {QUESTION_MAX_LENGTH}
                    </span>
                </div>
            </form>

            {!searched && children}

            {searched && (
                <>
                    {searchLoading && <LoadingState label="検索中..." />}

                    {!searchLoading && searchError && (
                        <StatusMessage
                            variant="error"
                            message="検索に失敗しました。"
                            onRetry={() => runSearch(query)}
                        />
                    )}

                    {!searchLoading && !searchError && results.length === 0 && (
                        <StatusMessage message="関連する質問が見つかりませんでした。" />
                    )}

                    {!searchLoading && !searchError && results.length > 0 && (
                        <div className="flex flex-col gap-3">
                            {results.map((result) => (
                                <Link key={result.id} href={`/questions/${result.id}`}>
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
                                            variant="preview"
                                        />
                                    </Card>
                                </Link>
                            ))}
                        </div>
                    )}

                    {!searchLoading && (
                        <div className="flex flex-col items-start gap-2 rounded-md border border-gray-200 bg-gray-50 p-4">
                            <p className="text-sm text-gray-600">
                                目的の質問はありませんか？
                            </p>
                            <Button
                                type="button"
                                variant="secondary"
                                disabled={ragLoading || trimmedLength < QUESTION_MIN_LENGTH}
                                onClick={() => runRag(query)}
                            >
                                AIに質問する
                            </Button>
                        </div>
                    )}

                    {ragLoading && <LoadingState label="回答を生成中..." />}

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
