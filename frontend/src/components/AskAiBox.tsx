"use client";

import { FormEvent, useState } from "react";
import { askAi } from "@/lib/api";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import LoadingState from "@/components/ui/LoadingState";
import { showToast } from "@/components/ui/Toast";

const inputClassName =
    "w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

export default function AskAiBox() {
    const [question, setQuestion] = useState("");
    const [answer, setAnswer] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
        e.preventDefault();

        const trimmed = question.trim();
        if (!trimmed) {
            return;
        }

        setLoading(true);
        setAnswer(null);

        try {
            const result = await askAi(trimmed);
            setAnswer(result.answer);
        } catch (error) {
            console.error(error);
            showToast("AIへの質問に失敗しました。", "error");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col gap-3">
            <h2 className="text-lg font-semibold text-gray-900">
                AIに質問する
            </h2>

            <form onSubmit={handleSubmit} className="flex gap-2">
                <input
                    type="text"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="物理に関する質問を入力してください"
                    className={inputClassName}
                />

                <Button
                    type="submit"
                    disabled={loading || !question.trim()}
                    className="shrink-0"
                >
                    質問する
                </Button>
            </form>

            {loading && <LoadingState label="回答を生成中..." />}

            {!loading && answer && (
                <Card className="whitespace-pre-wrap text-sm text-gray-700">
                    {answer}
                </Card>
            )}
        </div>
    );
}
