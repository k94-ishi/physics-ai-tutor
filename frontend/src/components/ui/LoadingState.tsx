"use client";

import { useLanguage } from "@/lib/i18n/LanguageContext";

type LoadingStateProps = {
    label?: string;
};

export default function LoadingState({ label }: LoadingStateProps) {
    const { t } = useLanguage();
    const resolvedLabel = label ?? t("common.loading");

    return (
        <div
            role="status"
            className="flex items-center gap-2 py-8 text-sm text-gray-500"
        >
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-gray-600" />
            {resolvedLabel}
        </div>
    );
}
