"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { fetchQuestions, deleteQuestion } from "@/lib/api";
import { Question } from "@/types/question";
import Card from "@/components/ui/Card";
import Button, { buttonClassName } from "@/components/ui/Button";
import LoadingState from "@/components/ui/LoadingState";
import StatusMessage from "@/components/ui/StatusMessage";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { showToast } from "@/components/ui/Toast";


export default function AdminQuestionsPage() {
    const [questions, setQuestions] = useState<Question[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);
    const [deleteTarget, setDeleteTarget] = useState<Question | null>(null);
    const [deleting, setDeleting] = useState(false);


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

    if (loading) {
        return <LoadingState />;
    }

    return (
        <main className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-gray-900">
                    質問管理
                </h1>

                <Link
                    href="/admin/questions/new"
                    className={buttonClassName("primary")}
                >
                    新規登録
                </Link>
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
                                <span className="line-clamp-1 text-gray-900">
                                    {question.question}
                                </span>

                                <div className="flex shrink-0 items-center gap-2">
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
        </main>
    );
}
