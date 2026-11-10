"use client";

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
import QuestionPreviewModal, {
    PreviewQuestion,
} from "@/components/ui/QuestionPreviewModal";
import ConceptChips from "@/components/ui/ConceptChips";
import MeaningChooser from "@/components/ui/MeaningChooser";
import { ConceptSearchItem } from "@/types/concept";
import { useQueryState } from "@/lib/hooks/useQueryState";
import { useLanguage } from "@/lib/i18n/LanguageContext";

type Mode = "similarity" | "keyword";

const KEYWORD_DEBOUNCE_MS = 300;
// カードではタグを少なめに出し、残りは「ほかN件」で開く。
const CARD_TAGS_VISIBLE = 5;

const LIST_QUERY_DEFAULTS = {
    page: "1",
    size: "30",
    keyword: "",
    // 概念チップ([41])からの絞り込み。空文字なら絞り込みなし。
    concept: "",
    // 意味(概念ID)で絞り込むとき([55])。conceptは見出し用の表示名。
    conceptId: "",
    // ベクトル検索([49])。値はQuestionSearchAndAskが管理し、ここでは
    // 初期タブの選択にだけ使う。
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

    // 一覧(pagination + keyword filter、page/size/keywordはURLで管理)
    const [queryState, setQueryState] = useQueryState(LIST_QUERY_DEFAULTS);
    // 共有リンクが正しいタブで開くよう、初期タブはURLから決める:
    // ?similar=はベクトル検索、?keyword=だけならキーワード検索。
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
    const listRequestId = useRef(0);
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
            const requestId = ++listRequestId.current;
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
        [language]
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

    // ページ・サイズ・キーワード・検索対象フィールドが確定するたびに一覧を取得する(初回ロードも含む)
    useEffect(() => {
        // 言語の解決前に取得すると、jaで一度取ってから取り直す([53])。
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
    ]);

    const handlePageChange = (nextPage: number) =>
        setQueryState({ page: String(nextPage) });
    const handleSizeChange = (nextSize: number) =>
        setQueryState({ size: String(nextSize), page: "1" });

    // 検索対象(質問/回答)は最低1つはオンのまま維持する(両方オフだと絞り込みが崩れるため)。
    const toggleSearchQuestion = () => {
        setSearchQuestion((prev) => (prev && !searchAnswer ? prev : !prev));
    };
    const toggleSearchAnswer = () => {
        setSearchAnswer((prev) => (prev && !searchQuestion ? prev : !prev));
    };

    // 「AIに聞く-検索/生成」タブでまだ検索していない間のフォールバックにも、
    // 「キーワード検索」タブの主表示にも、同じ質問一覧を使う(重複させない)。
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
                            <Card
                                key={question.id}
                                className="flex flex-col gap-2 transition-colors hover:border-blue-300 hover:bg-blue-50/50"
                            >
                                {/* Opens the preview; tags below stay separate links ([56]). */}
                                <button
                                    type="button"
                                    onClick={() => setPreview(question)}
                                    className="flex w-full cursor-pointer flex-col gap-1 text-left"
                                >
                                    <span className="font-medium text-gray-900">
                                        {question.question}
                                    </span>

                                    <MarkdownContent
                                        content={question.answer}
                                        variant="preview"
                                    />
                                </button>

                                {/* Tags are links, so they sit beside the preview button. */}
                                <ConceptChips
                                    concepts={question.concepts}
                                    visible={CARD_TAGS_VISIBLE}
                                />

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
