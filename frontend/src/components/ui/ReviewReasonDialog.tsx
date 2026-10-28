"use client";

import { useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import SelectField from "@/components/ui/SelectField";
import { REVIEW_REASONS, ReviewReason } from "@/types/question";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { TranslationKey } from "@/lib/i18n/translations";

type ReviewReasonDialogProps = {
    open: boolean;
    title: string;
    description?: string;
    confirming?: boolean;
    onConfirm: (reason: ReviewReason, comment: string | undefined) => void;
    onCancel: () => void;
};

export function reasonLabelKey(reason: ReviewReason): TranslationKey {
    return `reviewReason.${reason}` as TranslationKey;
}

/** Reason picker shown before a reject or edit-approve review is sent. */
export default function ReviewReasonDialog({
    open,
    title,
    description,
    confirming = false,
    onConfirm,
    onCancel,
}: ReviewReasonDialogProps) {
    const { t } = useLanguage();
    const [reason, setReason] = useState<ReviewReason>("PHYSICS_ERROR");
    const [comment, setComment] = useState("");
    const [error, setError] = useState(false);

    useEffect(() => {
        if (open) {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setReason("PHYSICS_ERROR");
            setComment("");
            setError(false);
        }
    }, [open]);

    useEffect(() => {
        if (!open) {
            return;
        }

        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === "Escape") {
                onCancel();
            }
        };

        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [open, onCancel]);

    if (!open) {
        return null;
    }

    const handleConfirm = () => {
        // Mirrors the API rule: OTHER is meaningless without an explanation.
        if (reason === "OTHER" && comment.trim() === "") {
            setError(true);
            return;
        }

        onConfirm(reason, comment.trim() === "" ? undefined : comment.trim());
    };

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
            role="dialog"
            aria-modal="true"
            aria-labelledby="review-reason-dialog-title"
        >
            <div className="flex w-full max-w-sm flex-col gap-4 rounded-lg bg-white p-6 shadow-lg">
                <h2
                    id="review-reason-dialog-title"
                    className="text-lg font-semibold text-gray-900"
                >
                    {title}
                </h2>

                {description && (
                    <p className="text-sm text-gray-600">{description}</p>
                )}

                <SelectField
                    id="review-reason"
                    label={t("reviewReason.reasonLabel")}
                    value={reason}
                    onChange={(e) => {
                        setReason(e.target.value as ReviewReason);
                        setError(false);
                    }}
                    options={REVIEW_REASONS.map((code) => ({
                        value: code,
                        label: t(reasonLabelKey(code)),
                    }))}
                />

                <label className="flex flex-col gap-1.5 text-sm font-medium text-gray-700">
                    {t("reviewReason.commentLabel")}
                    <textarea
                        value={comment}
                        onChange={(e) => {
                            setComment(e.target.value);
                            setError(false);
                        }}
                        rows={3}
                        className={`rounded-md border px-3 py-2 text-sm font-normal text-gray-900 focus:outline-none focus:ring-1 focus:ring-blue-500 ${
                            error ? "border-red-400" : "border-gray-300"
                        }`}
                    />
                </label>

                <div className="flex justify-end gap-2">
                    <Button
                        type="button"
                        variant="secondary"
                        onClick={onCancel}
                        disabled={confirming}
                    >
                        {t("common.cancel")}
                    </Button>

                    <Button
                        type="button"
                        onClick={handleConfirm}
                        disabled={confirming}
                    >
                        {confirming
                            ? t("common.processing")
                            : t("reviewReason.confirm")}
                    </Button>
                </div>
            </div>
        </div>
    );
}
