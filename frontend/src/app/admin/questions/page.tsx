"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { fetchQuestions, deleteQuestion } from "@/lib/api";
import { Question } from "@/types/question";


export default function AdminQuestionsPage() {
    const [questions, setQuestions] = useState<Question[]>([]);
    const [loading, setLoading] = useState(true);


    const loadQuestions = useCallback(async () => {
        try {
            const data = await fetchQuestions();
            setQuestions(data);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        loadQuestions();
    }, [loadQuestions]);

    const handleDelete = async (id: number) => {
        const confirmed = window.confirm(
            "この質問を削除しますか？"
        );

        if (!confirmed) {
            return;
        }

        try {
            await deleteQuestion(id);
            await loadQuestions();
        } catch (error) {
            console.error(error);
            alert("質問の削除に失敗しました");
        }
    };
    
    if (loading) {
        return <div>Loading...</div>;
    }

    return (
        <main>
            <h1>
                質問管理
            </h1>

            <a href="/admin/questions/new">
                新規登録
            </a>

            <ul>
                {questions.map((question) => (
                    <li key={question.id}>
                        <span>
                            {question.question}
                        </span>
                        
                        <Link
                        href={`/admin/questions/${question.id}/edit`}
                        >
                            編集
                        </Link>

                        <button
                            onClick={() => handleDelete(question.id)}
                        >
                            削除
                        </button>
                    </li>
                ))}
            </ul>
        </main>
    );
}