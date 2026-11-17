"use client";

import { useState } from "react";
import Link from "next/link";
import { useLanguage } from "@/lib/i18n/LanguageContext";

/** Tags shown before "more", so one answer does not fill the screen. */
export const VISIBLE_CONCEPTS = 8;

type ConceptChipsProps = {
    concepts: string[];
    /** How many tags show before "more"; cards use a smaller number. */
    visible?: number;
};

/** Tags as chips linking to their question lists, shortest first ([41]). */
export default function ConceptChips({
    concepts,
    visible = VISIBLE_CONCEPTS,
}: ConceptChipsProps) {
    const { t } = useLanguage();
    const [expanded, setExpanded] = useState(false);

    if (concepts.length === 0) {
        return null;
    }

    const ordered = [...concepts].sort((a, b) => a.length - b.length);
    const shown = expanded ? ordered : ordered.slice(0, visible);
    const hidden = ordered.length - shown.length;

    return (
        <ul
            aria-label={t("concepts.listLabel")}
            className="flex flex-wrap items-center gap-2"
        >
            {shown.map((concept) => (
                <li key={concept}>
                    <Link
                        href={`/?concept=${encodeURIComponent(concept)}`}
                        className="inline-flex rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 transition-colors hover:bg-blue-100"
                        title={t("concepts.chipTitle", { concept })}
                    >
                        {concept}
                    </Link>
                </li>
            ))}

            {hidden > 0 && (
                <li>
                    <button
                        type="button"
                        onClick={() => setExpanded(true)}
                        className="inline-flex cursor-pointer rounded-full border border-gray-300 px-3 py-1 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-50"
                    >
                        {t("concepts.showMore", { count: hidden })}
                    </button>
                </li>
            )}
        </ul>
    );
}
