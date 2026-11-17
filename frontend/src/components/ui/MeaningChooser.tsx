"use client";

import { useEffect, useState } from "react";
import { searchConcepts } from "@/lib/api";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { ConceptSearchItem } from "@/types/concept";
import { ContentLanguage } from "@/types/question";

/** A sense's label plus its explanation when it has one. */
export function senseLabel(item: ConceptSearchItem): string {
    return item.gloss ? `${item.label} — ${item.gloss}` : item.label;
}

type MeaningChooserProps = {
    word: string;
    onSelect: (item: ConceptSearchItem) => void;
};

/** When a tag's word has several meanings, let the student pick one ([55]). */
export default function MeaningChooser({
    word,
    onSelect,
}: MeaningChooserProps) {
    const { language, t } = useLanguage();
    const [senses, setSenses] = useState<ConceptSearchItem[]>([]);

    useEffect(() => {
        let cancelled = false;
        const key = word.normalize("NFKC").trim().toLowerCase();
        searchConcepts(word, language as ContentLanguage)
            .then((found) => {
                if (!cancelled) {
                    setSenses(
                        found.filter(
                            (item) =>
                                item.matched_term
                                    ?.normalize("NFKC")
                                    .toLowerCase() === key,
                        ),
                    );
                }
            })
            .catch((error) => console.error(error));
        return () => {
            cancelled = true;
        };
    }, [word, language]);

    if (senses.length < 2) {
        return null;
    }

    return (
        <div className="flex flex-col gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            <span>{t("conceptFilter.meanings", { word })}</span>
            <div className="flex flex-wrap gap-2">
                {senses.map((item) => (
                    <button
                        key={item.id}
                        type="button"
                        onClick={() => onSelect(item)}
                        className="cursor-pointer rounded-full border border-amber-300 bg-white px-3 py-1 text-xs font-medium hover:bg-amber-100"
                    >
                        {senseLabel(item)} ({item.question_count})
                    </button>
                ))}
            </div>
        </div>
    );
}
