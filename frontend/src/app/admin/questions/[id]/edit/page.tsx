"use client";

import {
    SyntheticEvent,
    useCallback,
    useEffect,
    useState,
} from "react";
import { useParams, useRouter } from "next/navigation";
import { fetchQuestion, updateQuestion } from "@/lib/api";
import Card from "@/components/ui/Card";
import FormField from "@/components/ui/FormField";
import Button from "@/components/ui/Button";
import LoadingState from "@/components/ui/LoadingState";
import StatusMessage from "@/components/ui/StatusMessage";
import { showToast } from "@/components/ui/Toast";

type FormErrors = {
    question?: string;
    answer?: string;
};

export default function EditQuestionPage() {
    const router = useRouter();
    const params = useParams();
    const id = Number(params.id);
    const [question, setQuestion] = useState("");
    const [answer, setAnswer] = useState("");
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [errors, setErrors] = useState<FormErrors>({});

    const loadQuestion = useCallback(async () => {
        setLoading(true);
        setLoadError(false);

        try {
            const data = await fetchQuestion(id);
            setQuestion(data.question);
            setAnswer(data.answer);
        } catch (error) {
            console.error(error);
            setLoadError(true);
        } finally {
            setLoading(false);
        }
    }, [id]);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        loadQuestion();
    }, [loadQuestion]);

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

        setSubmitting(true);
        try {
            await updateQuestion({
                id,
                question,
                answer,
            });
            showToast("更新しました。");
            router.push("/admin/questions");
        } catch (error) {
            console.error(error);
            showToast("更新に失敗しました。", "error");
            setSubmitting(false);
        }
    };

    if (loading) {
        return <LoadingState />;
    }

    if (loadError) {
        return (
            <StatusMessage
                variant="error"
                message="質問を取得できませんでした。"
                onRetry={loadQuestion}
            />
        );
    }

    return (
        <main className="flex flex-col gap-6">
            <h1 className="text-2xl font-bold text-gray-900">質問編集</h1>

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
                            setQuestion(e.target.value)
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
                            setAnswer(e.target.value)
                        }
                        rows={6}
                    />

                    <Button
                        type="submit"
                        disabled={submitting}
                        className="self-start"
                    >
                        {submitting ? "保存中..." : "保存"}
                    </Button>
                </form>
            </Card>
        </main>
    );
}
