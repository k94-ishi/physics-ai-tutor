"use client";

import { DragEvent, SyntheticEvent, useState } from "react";
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

function formatFileSize(bytes: number): string {
    if (bytes < 1024) {
        return `${bytes} B`;
    }
    return `${(bytes / 1024).toFixed(1)} KB`;
}

export default function UploadQuestionsPage() {
    const router = useRouter();

    const [file, setFile] = useState<File | null>(null);
    const [source, setSource] = useState<QuestionSource>("AI_GENERATED");
    const [status, setStatus] = useState<QuestionStatus>("UNREVIEWED");
    const [loading, setLoading] = useState(false);
    const [errors, setErrors] = useState<FormErrors>({});
    const [dragActive, setDragActive] = useState(false);

    const validate = (): FormErrors => {
        const nextErrors: FormErrors = {};

        if (!file) {
            nextErrors.file = "JSONLファイルを選択してください。";
        }

        return nextErrors;
    };

    const selectFile = (nextFile: File | null) => {
        setFile(nextFile);
        setErrors({});
    };

    const handleDragOver = (e: DragEvent<HTMLLabelElement>) => {
        e.preventDefault();
        setDragActive(true);
    };

    const handleDragLeave = (e: DragEvent<HTMLLabelElement>) => {
        e.preventDefault();
        setDragActive(false);
    };

    const handleDrop = (e: DragEvent<HTMLLabelElement>) => {
        e.preventDefault();
        setDragActive(false);

        const dropped = e.dataTransfer.files?.[0];
        if (dropped) {
            selectFile(dropped);
        }
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
            if (error instanceof ApiError && error.status === 422) {
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
                        <label className="text-sm font-medium text-gray-700">
                            JSONLファイル
                            <span className="ml-1 text-red-600" aria-hidden="true">
                                *
                            </span>
                        </label>

                        <label
                            htmlFor="file"
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onDrop={handleDrop}
                            className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed px-4 py-8 text-center transition-colors ${
                                dragActive
                                    ? "border-blue-500 bg-blue-50"
                                    : "border-gray-300 bg-gray-50 hover:bg-gray-100"
                            }`}
                        >
                            <span className="text-sm text-gray-600">
                                ファイルをドラッグ&ドロップ、またはクリックして選択
                            </span>
                            <span className="text-xs text-gray-400">
                                .jsonl形式のファイル
                            </span>

                            <input
                                id="file"
                                type="file"
                                accept=".jsonl"
                                onChange={(e) =>
                                    selectFile(e.target.files?.[0] ?? null)
                                }
                                className="hidden"
                            />
                        </label>

                        {file && (
                            <p className="text-sm text-gray-700">
                                選択中のファイル: {file.name}({formatFileSize(file.size)})
                            </p>
                        )}

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
