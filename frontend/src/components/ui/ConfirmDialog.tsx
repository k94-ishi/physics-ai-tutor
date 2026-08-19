"use client";

import { ReactNode, useEffect } from "react";
import Button from "@/components/ui/Button";
import { useLanguage } from "@/lib/i18n/LanguageContext";

type ConfirmDialogProps = {
    open: boolean;
    title: string;
    description?: ReactNode;
    confirmLabel?: string;
    cancelLabel?: string;
    confirming?: boolean;
    onConfirm: () => void;
    onCancel: () => void;
};

export default function ConfirmDialog({
    open,
    title,
    description,
    confirmLabel,
    cancelLabel,
    confirming = false,
    onConfirm,
    onCancel,
}: ConfirmDialogProps) {
    const { t } = useLanguage();
    const resolvedConfirmLabel = confirmLabel ?? t("common.delete");
    const resolvedCancelLabel = cancelLabel ?? t("common.cancel");

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

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirm-dialog-title"
        >
            <div className="w-full max-w-sm rounded-lg bg-white p-6 shadow-lg">
                <h2
                    id="confirm-dialog-title"
                    className="text-lg font-semibold text-gray-900"
                >
                    {title}
                </h2>

                {description && (
                    <p className="mt-2 text-sm text-gray-600">
                        {description}
                    </p>
                )}

                <div className="mt-6 flex justify-end gap-2">
                    <Button
                        type="button"
                        variant="secondary"
                        onClick={onCancel}
                        disabled={confirming}
                    >
                        {resolvedCancelLabel}
                    </Button>

                    <Button
                        type="button"
                        variant="danger"
                        onClick={onConfirm}
                        disabled={confirming}
                    >
                        {confirming ? t("common.processing") : resolvedConfirmLabel}
                    </Button>
                </div>
            </div>
        </div>
    );
}
