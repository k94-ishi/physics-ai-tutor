"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { fetchQuestions } from "@/lib/api";
import { Question } from "@/types/question";
import Card from "@/components/ui/Card";
import LoadingState from "@/components/ui/LoadingState";
import StatusMessage from "@/components/ui/StatusMessage";


export default function QuestionList() {
    const [questions, setQuestions] = useState<Question[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    const loadQuestions = useCallback(async () => {
        setLoading(true);
        setError(false);

        try {
            const data = await fetchQuestions();
            setQuestions(data);
        } catch (error) {
            console.error(error);
            setError(true);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        loadQuestions();
    }, [loadQuestions]);

    return (
        <div className="flex flex-col gap-4">
            <h2 className="text-lg font-semibold text-gray-900">
                質問一覧
            </h2>

            {loading && <LoadingState />}

            {!loading && error && (
                <StatusMessage
                    variant="error"
                    message="質問を取得できませんでした。"
                    onRetry={loadQuestions}
                />
            )}

            {!loading && !error && questions.length === 0 && (
                <StatusMessage message="登録されている質問がありません。" />
            )}

            {!loading && !error && questions.length > 0 && (
                <div className="flex flex-col gap-3">
                    {questions.map((question) => (
                        <Link
                            key={question.id}
                            href={`/questions/${question.id}`}
                        >
                            <Card className="transition-colors hover:border-blue-300 hover:bg-blue-50/50">
                                {question.question}
                            </Card>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    )
};
