"use client";

import { useEffect } from "react";
import Button from "@/components/ui/Button";
import { useLanguage } from "@/lib/i18n/LanguageContext";

export default function Error({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    const { t } = useLanguage();

    useEffect(() => {
        console.error(error);
    }, [error]);

    return (
        <main className="flex flex-col items-start gap-4">
            <h1 className="text-xl font-bold text-gray-900">
                {t("errorPage.title")}
            </h1>

            <p className="text-sm text-gray-600">
                {t("errorPage.description")}
            </p>

            <Button onClick={() => reset()}>{t("errorPage.retry")}</Button>
        </main>
    );
}
