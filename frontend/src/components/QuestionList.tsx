"use client";

import Link from "next/link";
import {
    FormEvent,
    Suspense,
    useCallback,
    useEffect,
    useRef,
    useState,
} from "react";
import { askAi, fetchQuestions, searchQuestions } from "@/lib/api";
import { Question, SimilarQuestion } from "@/types/question";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import LoadingState from "@/components/ui/LoadingState";
import StatusMessage from "@/components/ui/StatusMessage";
import Pagination from "@/components/ui/Pagination";
import MarkdownContent from "@/components/ui/MarkdownContent";
import { showToast } from "@/components/ui/Toast";
import { useQueryState } from "@/lib/hooks/useQueryState";

type Mode = "similarity" | "keyword" | "ask";

const SIMILARITY_LIMIT = 10;
const KEYWORD_DEBOUNCE_MS = 300;

const LIST_QUERY_DEFAULTS = {
    page: "1",
    size: "30",
    keyword: "",
};

function similarityPercent(distance: number): number {
    return Math.max(0, Math.round((1 - distance) * 100));
}

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
    const [mode, setMode] = useState<Mode>("similarity");

    // 一覧(pagination + keyword filter、page/size/keywordはURLで管理)
    const [queryState, setQueryState] = useQueryState(LIST_QUERY_DEFAULTS);
    const page = Number(queryState.page);
    const size = Number(queryState.size);
    const [keywordInput, setKeywordInput] = useState(queryState.keyword);
    const [listItems, setListItems] = useState<Question[]>([]);
    const [listTotal, setListTotal] = useState(0);
    const [listLoading, setListLoading] = useState(true);
    const [listError, setListError] = useState(false);
    const listRequestId = useRef(0);

    // 関連度検索(送信時のみ実行)
    const [similarityInput, setSimilarityInput] = useState("");
    const [similaritySearched, setSimilaritySearched] = useState(false);
    const [similarityResults, setSimilarityResults] = useState<
        SimilarQuestion[]
    >([]);
    const [similarityLoading, setSimilarityLoading] = useState(false);
    const [similarityError, setSimilarityError] = useState(false);
    const similarityRequestId = useRef(0);

    // AIに質問する(既存回答の検索ではなく、その場でAIが新しい回答を生成する)
    const [askInput, setAskInput] = useState("");
    const [askAnswer, setAskAnswer] = useState<string | null>(null);
    const [askLoading, setAskLoading] = useState(false);
    const askRequestId = useRef(0);

    const loadList = useCallback(
        async (targetPage: number, targetSize: number, keyword: string) => {
            const requestId = ++listRequestId.current;
            setListLoading(true);
            setListError(false);

            try {
                const data = await fetchQuestions({
                    page: targetPage,
                    size: targetSize,
                    keyword: keyword || undefined,
                    status: "APPROVED",
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

    // ページ・サイズ・キーワードが確定するたびに一覧を取得する(初回ロードも含む)
    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        loadList(page, size, queryState.keyword);
    }, [loadList, page, size, queryState.keyword]);

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

    const runAsk = useCallback(async (question: string) => {
        const trimmed = question.trim();

        if (!trimmed) {
            return;
        }

        const requestId = ++askRequestId.current;
        setAskLoading(true);
        setAskAnswer(null);

        try {
            const result = await askAi(trimmed);

            if (requestId !== askRequestId.current) {
                return;
            }

            setAskAnswer(result.answer);
        } catch (error) {
            if (requestId !== askRequestId.current) {
                return;
            }

            console.error(error);
            showToast("AIへの質問に失敗しました。", "error");
        } finally {
            if (requestId === askRequestId.current) {
                setAskLoading(false);
            }
        }
    }, []);

    const searchValue =
        mode === "similarity"
            ? similarityInput
            : mode === "ask"
                ? askInput
                : keywordInput;

    function handleInputChange(value: string) {
        if (mode === "similarity") {
            setSimilarityInput(value);
        } else if (mode === "ask") {
            setAskInput(value);
        } else {
            setKeywordInput(value);
        }
    }

    function handleSubmit(e: FormEvent<HTMLFormElement>) {
        e.preventDefault();
        if (mode === "similarity") {
            runSimilaritySearch(similarityInput);
        } else if (mode === "ask") {
            runAsk(askInput);
        }
    }

    const placeholder =
        mode === "similarity"
            ? "質問を入力すると意味が近い質問を検索します"
            : mode === "ask"
                ? "物理に関する質問を入力してください"
                : "キーワードで質問・回答を絞り込み";

    const isBusy = mode === "similarity" ? similarityLoading : askLoading;

    const showSimilarityView = mode === "similarity" && similaritySearched;
    const showAskView = mode === "ask";

    const handlePageChange = (nextPage: number) =>
        setQueryState({ page: String(nextPage) });
    const handleSizeChange = (nextSize: number) =>
        setQueryState({ size: String(nextSize), page: "1" });

    return (
        <div className="flex flex-col gap-4">
            <div className="flex gap-2">
                <button
                    type="button"
                    className={modeButtonClassName(mode === "similarity")}
                    onClick={() => setMode("similarity")}
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

                <button
                    type="button"
                    className={modeButtonClassName(mode === "ask")}
                    onClick={() => setMode("ask")}
                >
                    AIに質問する
                </button>
            </div>

            <form onSubmit={handleSubmit} className="flex gap-2">
                <input
                    type="text"
                    value={searchValue}
                    onChange={(e) => handleInputChange(e.target.value)}
                    placeholder={placeholder}
                    className={inputClassName}
                />

                {mode !== "keyword" && (
                    <Button
                        type="submit"
                        disabled={isBusy || !searchValue.trim()}
                        className="shrink-0"
                    >
                        {mode === "ask" ? "質問する" : "検索"}
                    </Button>
                )}
            </form>

            {showSimilarityView ? (
                <>
                    {similarityLoading && <LoadingState label="検索中..." />}

                    {!similarityLoading && similarityError && (
                        <StatusMessage
                            variant="error"
                            message="検索に失敗しました。"
                            onRetry={() =>
                                runSimilaritySearch(similarityInput)
                            }
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
                                        href={`/questions/${result.id}`}
                                    >
                                        <Card className="transition-colors hover:border-blue-300 hover:bg-blue-50/50">
                                            <div className="flex items-start justify-between gap-3">
                                                <span className="font-medium text-gray-900">
                                                    {result.question}
                                                </span>

                                                <span className="shrink-0 rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                                                    関連度{" "}
                                                    {similarityPercent(
                                                        result.distance
                                                    )}
                                                    %
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
                </>
            ) : showAskView ? (
                <>
                    {askLoading && <LoadingState label="回答を生成中..." />}

                    {!askLoading && askAnswer && (
                        <Card>
                            <MarkdownContent content={askAnswer} variant="full" />
                        </Card>
                    )}
                </>
            ) : (
                <>
                    {listLoading && <LoadingState />}

                    {!listLoading && listError && (
                        <StatusMessage
                            variant="error"
                            message="質問を取得できませんでした。"
                            onRetry={() =>
                                loadList(page, size, queryState.keyword)
                            }
                        />
                    )}

                    {!listLoading && !listError && listItems.length === 0 && (
                        <StatusMessage message="登録されている質問がありません。" />
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
                                    <Link
                                        key={question.id}
                                        href={`/questions/${question.id}`}
                                    >
                                        <Card className="transition-colors hover:border-blue-300 hover:bg-blue-50/50">
                                            <span className="font-medium text-gray-900">
                                                {question.question}
                                            </span>

                                            <MarkdownContent
                                                content={question.answer}
                                                variant="preview"
                                            />
                                        </Card>
                                    </Link>
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
