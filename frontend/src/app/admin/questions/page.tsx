"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { fetchQuestions, deleteQuestion, reviewQuestion } from "@/lib/api";
import { Question, QuestionStatus } from "@/types/question";
import Card from "@/components/ui/Card";
import Button, { buttonClassName } from "@/components/ui/Button";
import SelectField from "@/components/ui/SelectField";
import LoadingState from "@/components/ui/LoadingState";
import StatusMessage from "@/components/ui/StatusMessage";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { showToast } from "@/components/ui/Toast";

const STATUS_LABELS: Record<QuestionStatus, string> = {
    UNREVIEWED: "未レビュー",
    APPROVED: "承認済み",
    REJECTED: "却下",
};

const STATUS_BADGE_CLASSES: Record<QuestionStatus, string> = {
    UNREVIEWED: "bg-yellow-50 text-yellow-700",
    APPROVED: "bg-green-50 text-green-700",
    REJECTED: "bg-red-50 text-red-700",
};

type ReviewTarget = {
    question: Question;
    action: "APPROVE" | "REJECT";
};

export default function AdminQuestionsPage() {
    const [questions, setQuestions] = useState<Question[]>([]);
    const [statusFilter, setStatusFilter] = useState<QuestionStatus | "">("");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);
    const [deleteTarget, setDeleteTarget] = useState<Question | null>(null);
    const [deleting, setDeleting] = useState(false);
    const [reviewTarget, setReviewTarget] = useState<ReviewTarget | null>(null);
    const [reviewing, setReviewing] = useState(false);

    const loadQuestions = useCallback(async () => {
        setLoading(true);
        setError(false);

        try {
            const data = await fetchQuestions({
                status: statusFilter || undefined,
                size: 100,
            });
            setQuestions(data.items);
        } catch (error) {
            console.error(error);
            setError(true);
        } finally {
            setLoading(false);
        }
    }, [statusFilter]);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        loadQuestions();
    }, [loadQuestions]);

    const handleConfirmDelete = async () => {
        if (!deleteTarget) {
            return;
        }

        setDeleting(true);

        try {
            await deleteQuestion(deleteTarget.id);
            await loadQuestions();
            showToast("質問を削除しました。");
            setDeleteTarget(null);
        } catch (error) {
            console.error(error);
            showToast("質問の削除に失敗しました。", "error");
        } finally {
            setDeleting(false);
        }
    };

    const handleConfirmReview = async () => {
        if (!reviewTarget) {
            return;
        }

        setReviewing(true);

        try {
            await reviewQuestion(reviewTarget.question.id, {
                action: reviewTarget.action,
            });
            await loadQuestions();
            showToast(
                reviewTarget.action === "APPROVE"
                    ? "質問を承認しました。"
                    : "質問を却下しました。"
            );
            setReviewTarget(null);
        } catch (error) {
            console.error(error);
            showToast("処理に失敗しました。", "error");
        } finally {
            setReviewing(false);
        }
    };

    if (loading) {
        return <LoadingState />;
    }

    return (
        <main className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-gray-900">
                    質問管理
                </h1>

                <div className="flex items-center gap-2">
                    <Link
                        href="/admin/questions/upload"
                        className={buttonClassName("secondary")}
                    >
                        JSONLアップロード
                    </Link>

                    <Link
                        href="/admin/questions/new"
                        className={buttonClassName("primary")}
                    >
                        新規登録
                    </Link>
                </div>
            </div>

            <div className="max-w-xs">
                <SelectField
                    id="status-filter"
                    label="ステータスで絞り込み"
                    value={statusFilter}
                    onChange={(e) =>
                        setStatusFilter(e.target.value as QuestionStatus | "")
                    }
                    options={[
                        { value: "", label: "すべて" },
                        { value: "UNREVIEWED", label: "未レビュー" },
                        { value: "APPROVED", label: "承認済み" },
                        { value: "REJECTED", label: "却下" },
                    ]}
                />
            </div>

            {error && (
                <StatusMessage
                    variant="error"
                    message="質問一覧を取得できませんでした。"
                    onRetry={loadQuestions}
                />
            )}

            {!error && questions.length === 0 && (
                <StatusMessage message="登録されている質問がありません。" />
            )}

            {!error && questions.length > 0 && (
                <ul className="flex flex-col gap-3">
                    {questions.map((question) => (
                        <li key={question.id}>
                            <Card className="flex items-center justify-between gap-4">
                                <div className="flex min-w-0 flex-col gap-1">
                                    <div className="flex items-center gap-2">
                                        <span
                                            className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE_CLASSES[question.status]}`}
                                        >
                                            {STATUS_LABELS[question.status]}
                                        </span>
                                        <span className="line-clamp-1 text-gray-900">
                                            {question.question}
                                        </span>
                                    </div>
                                </div>

                                <div className="flex shrink-0 items-center gap-2">
                                    {question.status !== "APPROVED" && (
                                        <Button
                                            variant="secondary"
                                            onClick={() =>
                                                setReviewTarget({ question, action: "APPROVE" })
                                            }
                                        >
                                            承認
                                        </Button>
                                    )}

                                    {question.status !== "REJECTED" && (
                                        <Button
                                            variant="secondary"
                                            onClick={() =>
                                                setReviewTarget({ question, action: "REJECT" })
                                            }
                                        >
                                            却下
                                        </Button>
                                    )}

                                    <Link
                                        href={`/admin/questions/${question.id}/reviews`}
                                        className={buttonClassName("secondary")}
                                    >
                                        履歴
                                    </Link>

                                    <Link
                                        href={`/admin/questions/${question.id}/edit`}
                                        className={buttonClassName("secondary")}
                                    >
                                        編集
                                    </Link>

                                    <Button
                                        variant="danger"
                                        onClick={() => setDeleteTarget(question)}
                                    >
                                        削除
                                    </Button>
                                </div>
                            </Card>
                        </li>
                    ))}
                </ul>
            )}

            <ConfirmDialog
                open={deleteTarget !== null}
                title="質問を削除しますか？"
                description={deleteTarget?.question}
                confirming={deleting}
                onConfirm={handleConfirmDelete}
                onCancel={() => setDeleteTarget(null)}
            />

            <ConfirmDialog
                open={reviewTarget !== null}
                title={
                    reviewTarget?.action === "APPROVE"
                        ? "質問を承認しますか？"
                        : "質問を却下しますか？"
                }
                description={reviewTarget?.question.question}
                confirmLabel={reviewTarget?.action === "APPROVE" ? "承認" : "却下"}
                confirming={reviewing}
                onConfirm={handleConfirmReview}
                onCancel={() => setReviewTarget(null)}
            />
        </main>
    );
}
