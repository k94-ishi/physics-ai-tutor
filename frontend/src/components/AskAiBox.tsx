"use client";

import QuestionSearchAndAsk from "@/components/QuestionSearchAndAsk";
import { useLanguage } from "@/lib/i18n/LanguageContext";

export default function AskAiBox() {
    const { t } = useLanguage();

    return (
        <div className="flex flex-col gap-3">
            <h2 className="text-lg font-semibold text-gray-900">
                {t("askAiBox.heading")}
            </h2>

            <QuestionSearchAndAsk />
        </div>
    );
}
