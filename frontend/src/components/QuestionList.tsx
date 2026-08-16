"use client";

import Link from "next/link";
import { Suspense, useCallback, useEffect, useState, useRef } from "react";
import { fetchQuestions } from "@/lib/api";
import { Question } from "@/types/question";
import Card from "@/components/ui/Card";
import LoadingState from "@/components/ui/LoadingState";
import StatusMessage from "@/components/ui/StatusMessage";
import Pagination from "@/components/ui/Pagination";
import MarkdownContent from "@/components/ui/MarkdownContent";
import ReferencedQuestions from "@/components/ui/ReferencedQuestions";
import QuestionSearchAndAsk from "@/components/QuestionSearchAndAsk";
import { useQueryState } from "@/lib/hooks/useQueryState";

type Mode = "similarity" | "keyword";

const KEYWORD_DEBOUNCE_MS = 300;

const LIST_QUERY_DEFAULTS = {
    page: "1",
    size: "30",
    keyword: "",
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

    const handlePageChange = (nextPage: number) =>
        setQueryState({ page: String(nextPage) });
    const handleSizeChange = (nextSize: number) =>
        setQueryState({ size: String(nextSize), page: "1" });

    // 「関連QA検索/AI回答」タブでまだ検索していない間のフォールバックにも、
    // 「キーワード検索」タブの主表示にも、同じ質問一覧を使う(重複させない)。
    const browseList = (
        <>
            {listLoading && <LoadingState />}

            {!listLoading && listError && (
                <StatusMessage
                    variant="error"
                    message="質問を取得できませんでした。"
                    onRetry={() => loadList(page, size, queryState.keyword)}
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
                            <Card
                                key={question.id}
                                className="transition-colors hover:border-blue-300 hover:bg-blue-50/50"
                            >
                                <Link href={`/questions/${question.id}`}>
                                    <span className="font-medium text-gray-900">
                                        {question.question}
                                    </span>

                                    <MarkdownContent
                                        content={question.answer}
                                        variant="preview"
                                    />
                                </Link>

                                <ReferencedQuestions
                                    items={question.retrieved_questions}
                                />
                            </Card>
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
                    関連QA検索/AI回答
                </button>

                <button
                    type="button"
                    className={modeButtonClassName(mode === "keyword")}
                    onClick={() => setMode("keyword")}
                >
                    キーワード検索
                </button>
            </div>

            {mode === "similarity" ? (
                <QuestionSearchAndAsk>{browseList}</QuestionSearchAndAsk>
            ) : (
                <>
                    <input
                        type="text"
                        value={keywordInput}
                        onChange={(e) => setKeywordInput(e.target.value)}
                        placeholder="キーワードで質問・回答を絞り込み"
                        className={inputClassName}
                    />

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
