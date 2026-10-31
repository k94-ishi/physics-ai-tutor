"use client";

import { DragEvent, SyntheticEvent, useState } from "react";
import Link from "next/link";
import { ApiError, importQuestions } from "@/lib/api";
import { QuestionSource, QuestionStatus } from "@/types/question";
import Card from "@/components/ui/Card";
import SelectField from "@/components/ui/SelectField";
import Button, { buttonClassName } from "@/components/ui/Button";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { TranslationKey } from "@/lib/i18n/translations";

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

const RESULT_LABEL_KEYS: Record<FileResultStatus, TranslationKey> = {
    pending: "upload.resultPending",
    uploading: "upload.resultUploading",
    success: "upload.resultSuccess",
    duplicate: "upload.resultDuplicate",
    invalid: "upload.resultInvalid",
    error: "upload.resultError",
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
    const { t } = useLanguage();
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
            nextErrors.files = t("upload.fileRequired");
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
                let message = t("upload.uploadFailed");

                if (error instanceof ApiError && error.status === 422) {
                    fileStatus = "invalid";
                    message = t("upload.invalidFile");
                } else if (error instanceof ApiError && error.status === 409) {
                    fileStatus = "duplicate";
                    message = t("upload.duplicateFile");
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
                {t("upload.title")}
            </h1>

            <Card>
                <form
                    onSubmit={handleSubmit}
                    noValidate
                    className="flex flex-col gap-5"
                >
                    <div className="flex flex-col gap-1.5">
                        <label className="text-sm font-medium text-gray-700">
                            {t("upload.fileLabel")}
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
                                {t("upload.dropHint")}
                            </span>
                            <span className="text-xs text-gray-400">
                                {t("upload.dropFormat")}
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
                                                        ? t(
                                                              "upload.resultSuccessCount",
                                                              {
                                                                  count: result.createdCount,
                                                              }
                                                          )
                                                        : t(
                                                              RESULT_LABEL_KEYS[
                                                                  result.status
                                                              ]
                                                          )}
                                                </span>
                                            ) : (
                                                !submitting && (
                                                    <button
                                                        type="button"
                                                        onClick={() => removeFile(index)}
                                                        className="shrink-0 text-xs text-red-600 hover:underline"
                                                    >
                                                        {t("common.delete")}
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
                        label={t("upload.sourceLabel")}
                        value={source}
                        disabled={submitting}
                        onChange={(e) => setSource(e.target.value as QuestionSource)}
                        options={[
                            { value: "AI_GENERATED", label: t("upload.sourceAi") },
                            { value: "MANUAL", label: t("upload.sourceManual") },
                        ]}
                    />

                    <SelectField
                        id="status"
                        label={t("upload.statusLabel")}
                        value={status}
                        disabled={submitting}
                        onChange={(e) => setStatus(e.target.value as QuestionStatus)}
                        options={[
                            { value: "UNREVIEWED", label: t("admin.status.unreviewed") },
                            { value: "APPROVED", label: t("admin.status.approved") },
                            { value: "REJECTED", label: t("admin.status.rejected") },
                        ]}
                    />

                    <Button
                        type="submit"
                        disabled={submitting}
                        className="self-start"
                    >
                        {submitting ? t("common.registering") : t("common.register")}
                    </Button>
                </form>
            </Card>

            {showResults && allDone && (
                <Card className="flex flex-col gap-3">
                    <p className="text-sm text-gray-700">
                        {t("upload.summary", {
                            total: files.length,
                            success: successCount,
                            created: totalCreated,
                        })}
                    </p>

                    <Link
                        href="/admin/questions"
                        className={buttonClassName("primary", "self-start")}
                    >
                        {t("common.backToQuestions")}
                    </Link>
                </Card>
            )}
        </main>
    );
}
