"use client";

import { DragEvent, SyntheticEvent, useState } from "react";
import Link from "next/link";
import { ApiError, importQuestions } from "@/lib/api";
import { QuestionSource, QuestionStatus } from "@/types/question";
import Card from "@/components/ui/Card";
import SelectField from "@/components/ui/SelectField";
import Button, { buttonClassName } from "@/components/ui/Button";

type FormErrors = {
    files?: string;
};

type FileResultStatus =
    | "pending"
    | "uploading"
    | "success"
    | "duplicate"
    | "invalid"
    | "error";

type FileUploadResult = {
    fileName: string;
    status: FileResultStatus;
    createdCount?: number;
    message?: string;
};

const RESULT_LABELS: Record<FileResultStatus, string> = {
    pending: "待機中",
    uploading: "登録中...",
    success: "成功",
    duplicate: "重複エラー",
    invalid: "内容エラー",
    error: "失敗",
};

const RESULT_BADGE_CLASSES: Record<FileResultStatus, string> = {
    pending: "bg-gray-100 text-gray-500",
    uploading: "bg-blue-50 text-blue-700",
    success: "bg-green-50 text-green-700",
    duplicate: "bg-red-50 text-red-700",
    invalid: "bg-red-50 text-red-700",
    error: "bg-red-50 text-red-700",
};

function formatFileSize(bytes: number): string {
    if (bytes < 1024) {
        return `${bytes} B`;
    }
    return `${(bytes / 1024).toFixed(1)} KB`;
}

export default function UploadQuestionsPage() {
    const [files, setFiles] = useState<File[]>([]);
    const [source, setSource] = useState<QuestionSource>("AI_GENERATED");
    const [status, setStatus] = useState<QuestionStatus>("UNREVIEWED");
    const [submitting, setSubmitting] = useState(false);
    const [errors, setErrors] = useState<FormErrors>({});
    const [dragActive, setDragActive] = useState(false);
    const [results, setResults] = useState<FileUploadResult[]>([]);

    const validate = (): FormErrors => {
        const nextErrors: FormErrors = {};

        if (files.length === 0) {
            nextErrors.files = "JSONLファイルを選択してください。";
        }

        return nextErrors;
    };

    const addFiles = (incoming: FileList | File[]) => {
        const newFiles = Array.from(incoming);
        if (newFiles.length === 0) {
            return;
        }

        setFiles((prev) => [...prev, ...newFiles]);
        setErrors({});
        setResults([]);
    };

    const removeFile = (index: number) => {
        setFiles((prev) => prev.filter((_, i) => i !== index));
        setResults([]);
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
        addFiles(e.dataTransfer.files ?? []);
    };

    const handleSubmit = async (e: SyntheticEvent<HTMLFormElement>) => {
        e.preventDefault();

        const nextErrors = validate();
        setErrors(nextErrors);

        if (Object.keys(nextErrors).length > 0) {
            return;
        }

        setSubmitting(true);
        setResults(
            files.map((file) => ({ fileName: file.name, status: "pending" }))
        );

        for (let i = 0; i < files.length; i++) {
            setResults((prev) =>
                prev.map((result, index) =>
                    index === i ? { ...result, status: "uploading" } : result
                )
            );

            try {
                const result = await importQuestions(files[i], source, status);
                setResults((prev) =>
                    prev.map((r, index) =>
                        index === i
                            ? {
                                  ...r,
                                  status: "success",
                                  createdCount: result.created_count,
                              }
                            : r
                    )
                );
            } catch (error) {
                console.error(error);
                let fileStatus: FileResultStatus = "error";
                let message = "登録に失敗しました。";

                if (error instanceof ApiError && error.status === 422) {
                    fileStatus = "invalid";
                    message = "ファイルの内容に誤りがあります。";
                } else if (error instanceof ApiError && error.status === 409) {
                    fileStatus = "duplicate";
                    message = "既存の質問と重複する内容が含まれています。";
                }

                setResults((prev) =>
                    prev.map((r, index) =>
                        index === i
                            ? { ...r, status: fileStatus, message }
                            : r
                    )
                );
            }
        }

        setSubmitting(false);
    };

    const showResults = results.length > 0;
    const successCount = results.filter((r) => r.status === "success").length;
    const totalCreated = results.reduce(
        (sum, r) => sum + (r.createdCount ?? 0),
        0
    );
    const allDone =
        showResults &&
        results.every((r) => r.status !== "pending" && r.status !== "uploading");

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
                            JSONLファイル(複数選択可)
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
                                .jsonl形式のファイル(複数選択可)
                            </span>

                            <input
                                id="file"
                                type="file"
                                accept=".jsonl"
                                multiple
                                disabled={submitting}
                                onChange={(e) =>
                                    addFiles(e.target.files ?? [])
                                }
                                className="hidden"
                            />
                        </label>

                        {files.length > 0 && (
                            <ul className="flex flex-col gap-1">
                                {files.map((file, index) => {
                                    const result = results[index];

                                    return (
                                        <li
                                            key={`${file.name}-${file.size}-${index}`}
                                            className="flex items-center justify-between gap-2 rounded-md border border-gray-200 px-3 py-1.5 text-sm text-gray-700"
                                        >
                                            <span className="min-w-0 flex-1 truncate">
                                                {file.name}(
                                                {formatFileSize(file.size)})
                                            </span>

                                            {result ? (
                                                <span
                                                    className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${RESULT_BADGE_CLASSES[result.status]}`}
                                                >
                                                    {result.status === "success" &&
                                                    result.createdCount !== undefined
                                                        ? `成功(${result.createdCount}件)`
                                                        : RESULT_LABELS[result.status]}
                                                </span>
                                            ) : (
                                                !submitting && (
                                                    <button
                                                        type="button"
                                                        onClick={() => removeFile(index)}
                                                        className="shrink-0 text-xs text-red-600 hover:underline"
                                                    >
                                                        削除
                                                    </button>
                                                )
                                            )}
                                        </li>
                                    );
                                })}
                            </ul>
                        )}

                        {errors.files && (
                            <p className="text-sm text-red-600">{errors.files}</p>
                        )}
                    </div>

                    <SelectField
                        id="source"
                        label="登録元"
                        value={source}
                        disabled={submitting}
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
                        disabled={submitting}
                        onChange={(e) => setStatus(e.target.value as QuestionStatus)}
                        options={[
                            { value: "UNREVIEWED", label: "未レビュー" },
                            { value: "APPROVED", label: "承認済み" },
                            { value: "REJECTED", label: "却下" },
                        ]}
                    />

                    <Button
                        type="submit"
                        disabled={submitting}
                        className="self-start"
                    >
                        {submitting ? "登録中..." : "登録"}
                    </Button>
                </form>
            </Card>

            {showResults && allDone && (
                <Card className="flex flex-col gap-3">
                    <p className="text-sm text-gray-700">
                        {files.length}ファイル中{successCount}ファイルが成功し、
                        計{totalCreated}件の質問を登録しました。
                    </p>

                    <Link
                        href="/admin/questions"
                        className={buttonClassName("primary", "self-start")}
                    >
                        質問一覧へ戻る
                    </Link>
                </Card>
            )}
        </main>
    );
}
