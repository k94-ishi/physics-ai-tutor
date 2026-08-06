"use client";

import { SyntheticEvent, useState } from "react";
import { createQuestion } from "@/lib/api";
import Card from "@/components/ui/Card";
import FormField from "@/components/ui/FormField";
import Button from "@/components/ui/Button";
import { showToast } from "@/components/ui/Toast";

type FormErrors = {
    question?: string;
    answer?: string;
};

export default function NewQuestionPage() {
    const [question, setQuestion] = useState("");
    const [answer, setAnswer] = useState("");
    const [loading, setLoading] = useState(false);
    const [errors, setErrors] = useState<FormErrors>({});

    const validate = (): FormErrors => {
        const nextErrors: FormErrors = {};

        if (!question.trim()) {
            nextErrors.question = "質問を入力してください。";
        }

        if (!answer.trim()) {
            nextErrors.answer = "回答を入力してください。";
        }

        return nextErrors;
    };

    const handleSubmit = async (
        e: SyntheticEvent<HTMLFormElement>
    ) => {
        e.preventDefault();

        const nextErrors = validate();
        setErrors(nextErrors);

        if (Object.keys(nextErrors).length > 0) {
            return;
        }

        setLoading(true);
        try {
            await createQuestion({
                question,
                answer,
            });

            showToast("登録しました。");

            // フォームを初期化
            setQuestion("");
            setAnswer("");
        } catch (error) {
            console.error(error);
            showToast("登録に失敗しました。", "error");
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="flex flex-col gap-6">
            <h1 className="text-2xl font-bold text-gray-900">
                質問登録
            </h1>

            <Card>
                <form
                    onSubmit={handleSubmit}
                    noValidate
                    className="flex flex-col gap-5"
                >
                    <FormField
                        id="question"
                        label="質問"
                        required
                        error={errors.question}
                        value={question}
                        onChange={(e) =>
                            setQuestion(
                                e.target.value
                            )
                        }
                        rows={4}
                    />

                    <FormField
                        id="answer"
                        label="回答"
                        required
                        error={errors.answer}
                        value={answer}
                        onChange={(e) =>
                            setAnswer(
                                e.target.value
                            )
                        }
                        rows={6}
                    />

                    <Button
                        type="submit"
                        disabled={loading}
                        className="self-start"
                    >
                        {loading
                            ? "登録中..."
                            : "登録"}
                    </Button>
                </form>
            </Card>
        </main>
    )
}
