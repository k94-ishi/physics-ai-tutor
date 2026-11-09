"use client";

import { useEffect, useRef, useState } from "react";
import { searchConcepts } from "@/lib/api";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { ConceptSearchItem } from "@/types/concept";
import { ContentLanguage } from "@/types/question";

const SEARCH_DEBOUNCE_MS = 250;

type ConceptFilterProps = {
    onSelect: (item: ConceptSearchItem) => void;
};

/** A sense's label plus its explanation when it has one. */
export function senseLabel(item: ConceptSearchItem): string {
    return item.gloss ? `${item.label} — ${item.gloss}` : item.label;
}

/**
 * 概念を日本語でも英語でも探せる入力欄([41]/[55])。候補は「意味」単位で、
 * 同じ語が複数の意味を持つときは説明つきで別々に並ぶ。
 */
export default function ConceptFilter({ onSelect }: ConceptFilterProps) {
    const { language, t } = useLanguage();
    const [input, setInput] = useState("");
    const [items, setItems] = useState<ConceptSearchItem[]>([]);
    const [open, setOpen] = useState(false);
    const requestId = useRef(0);

    useEffect(() => {
        const trimmed = input.trim();
        if (trimmed === "") {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setItems([]);
            return;
        }
        const timer = setTimeout(async () => {
            const current = ++requestId.current;
            try {
                const found = await searchConcepts(
                    trimmed,
                    language as ContentLanguage
                );
                if (current === requestId.current) {
                    setItems(found);
                }
            } catch (error) {
                console.error(error);
            }
        }, SEARCH_DEBOUNCE_MS);
        return () => clearTimeout(timer);
    }, [input, language]);

    const choose = (item: ConceptSearchItem) => {
        onSelect(item);
        setInput("");
        setOpen(false);
    };

    return (
        <div className="relative flex flex-col gap-1">
            <label htmlFor="concept-filter-input" className="text-xs text-gray-600">
                {t("conceptFilter.label")}
            </label>
            <input
                id="concept-filter-input"
                type="text"
                role="combobox"
                aria-expanded={open && input.trim() !== ""}
                aria-controls="concept-filter-options"
                value={input}
                onChange={(e) => {
                    setInput(e.target.value);
                    setOpen(true);
                }}
                onKeyDown={(e) => {
                    if (e.key === "Escape") setOpen(false);
                    if (e.key === "Enter" && items.length > 0) {
                        e.preventDefault();
                        choose(items[0]);
                    }
                }}
                placeholder={t("conceptFilter.placeholder")}
                maxLength={100}
                className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />

            {open && input.trim() !== "" && (
                <ul
                    id="concept-filter-options"
                    role="listbox"
                    className="absolute top-full z-20 mt-1 max-h-72 w-full overflow-y-auto rounded-md border border-gray-200 bg-white py-1 shadow-lg"
                >
                    {items.length === 0 && (
                        <li className="px-3 py-2 text-sm text-gray-500">
                            {t("conceptFilter.noMatch")}
                        </li>
                    )}
                    {items.map((item) => (
                        <li key={item.id} role="option" aria-selected={false}>
                            <button
                                type="button"
                                onClick={() => choose(item)}
                                className="flex w-full cursor-pointer items-center justify-between gap-3 px-3 py-2 text-left text-sm hover:bg-blue-50"
                            >
                                <span className="text-gray-900">
                                    {senseLabel(item)}
                                    {item.matched_term &&
                                        item.matched_term !== item.label && (
                                            <span className="ml-2 text-xs text-gray-500">
                                                ({item.matched_term})
                                            </span>
                                        )}
                                </span>
                                <span className="shrink-0 text-xs text-gray-500">
                                    {t("conceptFilter.count", {
                                        count: item.question_count,
                                    })}
                                </span>
                            </button>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}

type MeaningChooserProps = {
    word: string;
    onSelect: (item: ConceptSearchItem) => void;
};

/** When a chip's word names several senses, let the student pick one. */
export function MeaningChooser({ word, onSelect }: MeaningChooserProps) {
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
                                item.matched_term?.normalize("NFKC").toLowerCase() ===
                                key
                        )
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
