"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchQuestions } from "@/lib/api";
import { Question } from "@/types/question";


export default function QuestionList() {
    const [questions, setQuestions] = useState<Question[]>([]);

    useEffect(() => {
        fetchQuestions()
        .then(setQuestions)
        .catch(() => {
            throw new Error("質問を取得できませんでした");
        });
    }, [])

    return (
        <>
            <h2>
                質問一覧
            </h2>

            {questions.map((question) => (
                <Link
                    key={question.id}
                    href={`/questions/${question.id}`}
                >
                    {question.question}
                </Link>
            ))}
        </>
    )
};

