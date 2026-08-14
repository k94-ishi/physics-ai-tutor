"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { fetchQuestionReviews } from "@/lib/api";
import { QuestionReview, QuestionReviewAction } from "@/types/question";
import Card from "@/components/ui/Card";
import LoadingState from "@/components/ui/LoadingState";
import StatusMessage from "@/components/ui/StatusMessage";

const ACTION_LABELS: Record<QuestionReviewAction, string> = {
    APPROVE: "承認",
    EDIT_APPROVE: "編集して承認",
    REJECT: "却下",
};

export default function QuestionReviewsPage() {
    const params = useParams();
    const id = Number(params.id);
    const [reviews, setReviews] = useState<QuestionReview[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    const loadReviews = useCallback(async () => {
        setLoading(true);
        setError(false);

        try {
            const data = await fetchQuestionReviews(id);
            setReviews(data);
        } catch (error) {
            console.error(error);
            setError(true);
        } finally {
            setLoading(false);
        }
    }, [id]);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        loadReviews();
    }, [loadReviews]);

    if (loading) {
        return <LoadingState />;
    }

    return (
        <main className="flex flex-col gap-6">
            <h1 className="text-2xl font-bold text-gray-900">
                レビュー履歴
            </h1>

            {error && (
                <StatusMessage
                    variant="error"
                    message="レビュー履歴を取得できませんでした。"
                    onRetry={loadReviews}
                />
            )}

            {!error && reviews.length === 0 && (
                <StatusMessage message="レビュー履歴がありません。" />
            )}

            {!error && reviews.length > 0 && (
                <ul className="flex flex-col gap-3">
                    {reviews.map((review) => (
                        <li key={review.id}>
                            <Card className="flex flex-col gap-2">
                                <div className="flex items-center justify-between">
                                    <span className="font-medium text-gray-900">
                                        {ACTION_LABELS[review.action]}
                                    </span>
                                    <span className="text-xs text-gray-500">
                                        {new Date(review.created_at).toLocaleString("ja-JP")}
                                    </span>
                                </div>

                                <span className="text-xs text-gray-500">
                                    レビュアーID: {review.reviewer_id}
                                </span>

                                {review.action === "EDIT_APPROVE" && (
                                    <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2">
                                        <div>
                                            <p className="text-xs font-medium text-gray-500">変更前</p>
                                            <p className="mt-1 whitespace-pre-wrap text-sm text-gray-700">
                                                {review.before_question}
                                            </p>
                                            <p className="mt-1 whitespace-pre-wrap text-sm text-gray-500">
                                                {review.before_answer}
                                            </p>
                                        </div>
                                        <div>
                                            <p className="text-xs font-medium text-gray-500">変更後</p>
                                            <p className="mt-1 whitespace-pre-wrap text-sm text-gray-700">
                                                {review.after_question}
                                            </p>
                                            <p className="mt-1 whitespace-pre-wrap text-sm text-gray-500">
                                                {review.after_answer}
                                            </p>
                                        </div>
                                    </div>
                                )}

                                {review.comment && (
                                    <p className="mt-1 text-sm text-gray-600">
                                        コメント: {review.comment}
                                    </p>
                                )}
                            </Card>
                        </li>
                    ))}
                </ul>
            )}
        </main>
    );
}
