"use client";

import { useLanguage } from "@/lib/i18n/LanguageContext";
import { showToast } from "@/components/ui/Toast";

type QuestionIdBadgeProps = {
    id: number;
};

/** Shows a question id as `#123`; clicking copies the number ([31]). */
export default function QuestionIdBadge({ id }: QuestionIdBadgeProps) {
    const { t } = useLanguage();

    const copy = async (event: React.MouseEvent) => {
        // The card is clickable too, so only copy here.
        event.stopPropagation();
        event.preventDefault();

        try {
            await navigator.clipboard.writeText(String(id));
            showToast(t("admin.questionIdCopied", { id }));
        } catch {
            // Without a clipboard, showing the id is enough.
        }
    };

    return (
        <button
            type="button"
            onClick={copy}
            title={t("admin.questionIdCopy", { id })}
            aria-label={t("admin.questionIdCopy", { id })}
            className="shrink-0 cursor-pointer rounded-full bg-gray-100 px-2 py-0.5 font-mono text-xs font-medium text-gray-600 hover:bg-gray-200"
        >
            #{id}
        </button>
    );
}
