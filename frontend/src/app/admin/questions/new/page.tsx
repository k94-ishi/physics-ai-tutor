"use client";

import { SyntheticEvent, useState } from "react";
import { createQuestion } from "@/lib/api";
import Card from "@/components/ui/Card";
import FormField from "@/components/ui/FormField";
import Button from "@/components/ui/Button";
import { showToast } from "@/components/ui/Toast";
import { useLanguage } from "@/lib/i18n/LanguageContext";

type FormErrors = {
    question?: string;
    answer?: string;
};

export default function NewQuestionPage() {
    const { t } = useLanguage();
    const [question, setQuestion] = useState("");
    const [answer, setAnswer] = useState("");
    const [loading, setLoading] = useState(false);
    const [errors, setErrors] = useState<FormErrors>({});

    const validate = (): FormErrors => {
        const nextErrors: FormErrors = {};

        if (!question.trim()) {
            nextErrors.question = t("form.questionRequired");
        }

        if (!answer.trim()) {
            nextErrors.answer = t("form.answerRequired");
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

            showToast(t("questionForm.registered"));

            // フォームを初期化
            setQuestion("");
            setAnswer("");
        } catch (error) {
            console.error(error);
            showToast(t("questionForm.registerFailed"), "error");
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="flex flex-col gap-6">
            <h1 className="text-2xl font-bold text-gray-900">
                {t("questionForm.newTitle")}
            </h1>

            <Card>
                <form
                    onSubmit={handleSubmit}
                    noValidate
                    className="flex flex-col gap-5"
                >
                    <FormField
                        id="question"
                        label={t("form.questionLabel")}
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
                        label={t("form.answerLabel")}
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
                            ? t("common.registering")
                            : t("common.register")}
                    </Button>
                </form>
            </Card>
        </main>
    )
}
