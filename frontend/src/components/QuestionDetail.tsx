"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, fetchQuestion, fetchRelatedQuestions } from "@/lib/api";
import { Question } from "@/types/question";
import Card from "@/components/ui/Card";
import LoadingState from "@/components/ui/LoadingState";
import MarkdownContent from "@/components/ui/MarkdownContent";
import ReferencedQuestions from "@/components/ui/ReferencedQuestions";
import StatusMessage from "@/components/ui/StatusMessage";
import { useLanguage } from "@/lib/i18n/LanguageContext";

type QuestionDetailProps = {
    id: number;
    matched?: string;
};

/**
 * Client-side question view: refetches in the active UI language, so
 * switching the header language switches the content too.
 */
export default function QuestionDetail({ id, matched }: QuestionDetailProps) {
    const { language, t } = useLanguage();
    const [question, setQuestion] = useState<Question | null>(null);
    const [related, setRelated] = useState<Question[]>([]);
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
            const relatedData = await fetchRelatedQuestions(id, 5, language);
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

                <ReferencedQuestions items={question.retrieved_questions} />
            </Card>

            {related.length > 0 && (
                <div className="flex flex-col gap-3">
                    <h2 className="text-lg font-semibold text-gray-900">
                        {t("questionDetail.relatedQuestions")}
                    </h2>

                    <div className="flex flex-col gap-3">
                        {related.map((item) => (
                            <Link key={item.id} href={`/questions/${item.id}`}>
                                <Card className="transition-colors hover:border-blue-300 hover:bg-blue-50/50">
                                    <span className="font-medium text-gray-900">
                                        {item.question}
                                    </span>

                                    <MarkdownContent
                                        content={item.answer}
                                        variant="preview"
                                    />
                                </Card>
                            </Link>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
