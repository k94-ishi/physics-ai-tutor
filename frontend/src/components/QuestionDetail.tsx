"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, fetchQuestion, fetchRelatedQuestions } from "@/lib/api";
import { Question } from "@/types/question";
import Card from "@/components/ui/Card";
import LoadingState from "@/components/ui/LoadingState";
import MarkdownContent from "@/components/ui/MarkdownContent";
import ConceptChips from "@/components/ui/ConceptChips";
import QuestionPreviewModal from "@/components/ui/QuestionPreviewModal";
import ReferencedQuestions from "@/components/ui/ReferencedQuestions";
import StatusMessage from "@/components/ui/StatusMessage";
import { useLanguage } from "@/lib/i18n/LanguageContext";

type QuestionDetailProps = {
    id: number;
    matched?: string;
};

// 1回の取得でAPIの上限まで取り、表示だけ段階的に増やす(追加の通信なし)。
const RELATED_FETCH_LIMIT = 20;
const RELATED_VISIBLE = 10;

/**
 * Client-side question view: refetches in the active UI language, so
 * switching the header language switches the content too.
 */
export default function QuestionDetail({ id, matched }: QuestionDetailProps) {
    const { language, t } = useLanguage();
    const [question, setQuestion] = useState<Question | null>(null);
    const [related, setRelated] = useState<Question[]>([]);
    const [relatedExpanded, setRelatedExpanded] = useState(false);
    const [preview, setPreview] = useState<Question | null>(null);
    const [loading, setLoading] = useState(true);
    const [notFoundError, setNotFoundError] = useState(false);
    const [loadError, setLoadError] = useState(false);
    const requestId = useRef(0);

    const load = useCallback(async () => {
        const current = ++requestId.current;
        setLoading(true);
        setLoadError(false);
        setNotFoundError(false);

        try {
            const data = await fetchQuestion(id, language);

            if (current !== requestId.current) {
                return;
            }
            setQuestion(data);
        } catch (error) {
            if (current !== requestId.current) {
                return;
            }
            if (error instanceof ApiError && error.status === 404) {
                setNotFoundError(true);
            } else {
                console.error(error);
                setLoadError(true);
            }
            setQuestion(null);
            setLoading(false);
            return;
        }

        try {
            const relatedData = await fetchRelatedQuestions(
                id,
                RELATED_FETCH_LIMIT,
                language
            );
            if (current === requestId.current) {
                setRelated(relatedData);
            }
        } catch (error) {
            console.error(error);
            if (current === requestId.current) {
                setRelated([]);
            }
        } finally {
            if (current === requestId.current) {
                setLoading(false);
            }
        }
    }, [id, language]);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        load();
    }, [load]);

    if (loading && question === null) {
        return <LoadingState />;
    }

    if (notFoundError) {
        return <StatusMessage message={t("questionList.empty")} />;
    }

    if (loadError || question === null) {
        return (
            <StatusMessage
                variant="error"
                message={t("questionList.fetchFailed")}
                onRetry={load}
            />
        );
    }

    const visibleRelated = relatedExpanded
        ? related
        : related.slice(0, RELATED_VISIBLE);
    const hiddenRelated = related.length - visibleRelated.length;

    const translatedBadge =
        question.provenance === "MACHINE"
            ? question.status === "APPROVED"
                ? t("questionDetail.autoTranslatedReviewed")
                : t("questionDetail.autoTranslated")
            : null;

    return (
        <div className="flex flex-col gap-6">
            <Card className="flex flex-col gap-4">
                {matched === "exact" && (
                    <p className="rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-700">
                        {t("questionDetail.alreadyAnswered")}
                    </p>
                )}

                <div className="flex flex-wrap items-center gap-2">
                    {question.status === "UNREVIEWED" && (
                        <span className="shrink-0 rounded-full bg-yellow-50 px-2 py-0.5 text-xs font-medium text-yellow-700">
                            {t("questionDetail.unreviewedBadge")}
                        </span>
                    )}

                    {translatedBadge && (
                        <span className="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                            {translatedBadge}
                        </span>
                    )}

                    <h1 className="text-xl font-bold text-gray-900">
                        {question.question}
                    </h1>
                </div>

                <MarkdownContent content={question.answer} variant="full" />

                <ConceptChips concepts={question.concepts} />

                <ReferencedQuestions items={question.retrieved_questions} />
            </Card>

            {related.length > 0 && (
                <div className="flex flex-col gap-3">
                    <h2 className="text-lg font-semibold text-gray-900">
                        {t("questionDetail.relatedQuestions")}
                    </h2>

                    <p className="text-xs text-gray-500">
                        {t("questionDetail.relatedHint")}
                    </p>

                    <div className="flex flex-col gap-3">
                        {visibleRelated.map((item) => (
                            <Card
                                key={item.id}
                                className="transition-colors hover:border-blue-300 hover:bg-blue-50/50"
                            >
                                <button
                                    type="button"
                                    onClick={() => setPreview(item)}
                                    className="flex w-full cursor-pointer flex-col gap-1 text-left"
                                >
                                    <span className="font-medium text-gray-900">
                                        {item.question}
                                    </span>

                                    <MarkdownContent
                                        content={item.answer}
                                        variant="preview"
                                    />
                                </button>
                            </Card>
                        ))}
                    </div>

                    {hiddenRelated > 0 && (
                        <button
                            type="button"
                            onClick={() => setRelatedExpanded(true)}
                            className="self-start cursor-pointer text-sm font-medium text-blue-700 underline underline-offset-2"
                        >
                            {t("questionDetail.showMoreRelated")}
                        </button>
                    )}
                </div>
            )}

            <QuestionPreviewModal
                question={preview}
                onClose={() => setPreview(null)}
            />
        </div>
    );
}
