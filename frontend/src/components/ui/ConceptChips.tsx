"use client";

import { useState } from "react";
import Link from "next/link";
import { useLanguage } from "@/lib/i18n/LanguageContext";

/** 1画面を概念で埋めないための初期表示数。残りは「もっと見る」で開く。 */
export const VISIBLE_CONCEPTS = 8;

type ConceptChipsProps = {
    concepts: string[];
};

/**
 * 回答が使っている概念をチップとして見せ、同じ概念の質問一覧へ送る([41])。
 * 概念はこのアプリが作る唯一の地図で、発展的な回答から前提へ降りる手がかり
 * になるため、管理画面だけでなく生徒にも見せる。
 *
 * 並べ替えは今は短い順。概念の中心性が使えるようになったらそれに置き換える。
 */
export default function ConceptChips({ concepts }: ConceptChipsProps) {
    const { t } = useLanguage();
    const [expanded, setExpanded] = useState(false);

    if (concepts.length === 0) {
        return null;
    }

    const ordered = [...concepts].sort((a, b) => a.length - b.length);
    const shown = expanded ? ordered : ordered.slice(0, VISIBLE_CONCEPTS);
    const hidden = ordered.length - shown.length;

    return (
        <section className="flex flex-col gap-2">
            <h2 className="text-sm font-medium text-gray-700">
                {t("concepts.heading")}
            </h2>

            <ul className="flex flex-wrap items-center gap-2">
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
        </section>
    );
}
