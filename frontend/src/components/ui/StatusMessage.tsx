"use client";

import { useLanguage } from "@/lib/i18n/LanguageContext";

type StatusMessageVariant = "empty" | "error";

type StatusMessageProps = {
    variant?: StatusMessageVariant;
    message: string;
    onRetry?: () => void;
};

const variantClasses: Record<StatusMessageVariant, string> = {
    empty: "border-dashed border-gray-300 bg-white text-gray-500",
    error: "border-red-200 bg-red-50 text-red-700",
};

export default function StatusMessage({
    variant = "empty",
    message,
    onRetry,
}: StatusMessageProps) {
    const { t } = useLanguage();

    return (
        <div
            role={variant === "error" ? "alert" : undefined}
            className={`flex flex-col items-center gap-3 rounded-md border px-4 py-10 text-center text-sm ${variantClasses[variant]}`}
        >
            <p>{message}</p>

            {onRetry && (
                <button
                    type="button"
                    onClick={onRetry}
                    className="font-medium underline underline-offset-2 hover:opacity-80"
                >
                    {t("common.retry")}
                </button>
            )}
        </div>
    );
}
