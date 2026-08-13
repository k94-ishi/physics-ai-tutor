"use client";

import { SyntheticEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, importQuestions } from "@/lib/api";
import { QuestionSource, QuestionStatus } from "@/types/question";
import Card from "@/components/ui/Card";
import SelectField from "@/components/ui/SelectField";
import Button from "@/components/ui/Button";
import { showToast } from "@/components/ui/Toast";

type FormErrors = {
    file?: string;
};

export default function UploadQuestionsPage() {
    const router = useRouter();

    const [file, setFile] = useState<File | null>(null);
    const [source, setSource] = useState<QuestionSource>("AI_GENERATED");
    const [status, setStatus] = useState<QuestionStatus>("UNREVIEWED");
    const [loading, setLoading] = useState(false);
    const [errors, setErrors] = useState<FormErrors>({});

    const validate = (): FormErrors => {
        const nextErrors: FormErrors = {};

        if (!file) {
            nextErrors.file = "JSONLファイルを選択してください。";
        }

        return nextErrors;
    };

    const handleSubmit = async (e: SyntheticEvent<HTMLFormElement>) => {
        e.preventDefault();

        const nextErrors = validate();
        setErrors(nextErrors);

        if (Object.keys(nextErrors).length > 0 || !file) {
            return;
        }

        setLoading(true);
        try {
            const result = await importQuestions(file, source, status);
            showToast(`${result.created_count}件の質問を登録しました。`);
            router.push("/admin/questions");
        } catch (error) {
            console.error(error);
            if (
                error instanceof ApiError &&
                error.status === 422
            ) {
                showToast("ファイルの内容に誤りがあります。", "error");
            } else if (error instanceof ApiError && error.status === 409) {
                showToast("既存の質問と重複する内容が含まれています。", "error");
            } else {
                showToast("登録に失敗しました。", "error");
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="flex flex-col gap-6">
            <h1 className="text-2xl font-bold text-gray-900">
                JSONLアップロード
            </h1>

            <Card>
                <form
                    onSubmit={handleSubmit}
                    noValidate
                    className="flex flex-col gap-5"
                >
                    <div className="flex flex-col gap-1.5">
                        <label
                            htmlFor="file"
                            className="text-sm font-medium text-gray-700"
                        >
                            JSONLファイル
                            <span className="ml-1 text-red-600" aria-hidden="true">
                                *
                            </span>
                        </label>

                        <input
                            id="file"
                            type="file"
                            accept=".jsonl"
                            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                            className="text-sm text-gray-700"
                        />

                        {errors.file && (
                            <p className="text-sm text-red-600">{errors.file}</p>
                        )}
                    </div>

                    <SelectField
                        id="source"
                        label="登録元"
                        value={source}
                        onChange={(e) => setSource(e.target.value as QuestionSource)}
                        options={[
                            { value: "AI_GENERATED", label: "AI生成" },
                            { value: "MANUAL", label: "手動" },
                        ]}
                    />

                    <SelectField
                        id="status"
                        label="登録時のステータス"
                        value={status}
                        onChange={(e) => setStatus(e.target.value as QuestionStatus)}
                        options={[
                            { value: "UNREVIEWED", label: "未レビュー" },
                            { value: "APPROVED", label: "承認済み" },
                            { value: "REJECTED", label: "却下" },
                        ]}
                    />

                    <Button
                        type="submit"
                        disabled={loading}
                        className="self-start"
                    >
                        {loading ? "登録中..." : "登録"}
                    </Button>
                </form>
            </Card>
        </main>
    );
}
