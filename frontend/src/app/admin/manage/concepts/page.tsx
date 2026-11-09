"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAdminConcepts } from "@/lib/api";
import Card from "@/components/ui/Card";
import LoadingState from "@/components/ui/LoadingState";
import Pagination from "@/components/ui/Pagination";
import StatusMessage from "@/components/ui/StatusMessage";
import ConceptEditor from "@/components/admin/ConceptEditor";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { AdminConcept, ConceptReviewFilter } from "@/types/concept";

const SEARCH_DEBOUNCE_MS = 300;
const FILTERS: ConceptReviewFilter[] = ["all", "review", "shared"];
const FILTER_KEYS = {
    all: "conceptsAdmin.filterAll",
    review: "conceptsAdmin.filterReview",
    shared: "conceptsAdmin.filterShared",
} as const;

function wordsOf(concept: AdminConcept, language: "ja" | "en"): string {
    return concept.terms
        .filter((term) => term.language === language)
        .map((term) => term.term)
        .join(" / ");
}

/** Admin list of concept senses with an inline editor ([55]). */
export default function AdminConceptsPage() {
    const { t } = useLanguage();
    const [query, setQuery] = useState("");
    const [filter, setFilter] = useState<ConceptReviewFilter>("all");
    const [page, setPage] = useState(1);
    const [size, setSize] = useState(30);
    const [items, setItems] = useState<AdminConcept[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [failed, setFailed] = useState(false);
    const [openId, setOpenId] = useState<number | null>(null);
    const requestId = useRef(0);

    const load = useCallback(async () => {
        const current = ++requestId.current;
        setLoading(true);
        setFailed(false);
        try {
            const data = await fetchAdminConcepts({ q: query.trim(), filter, page, size });
            if (current !== requestId.current) return;
            setItems(data.items);
            setTotal(data.total);
        } catch (error) {
            if (current !== requestId.current) return;
            console.error(error);
            setFailed(true);
        } finally {
            if (current === requestId.current) setLoading(false);
        }
    }, [query, filter, page, size]);

    useEffect(() => {
        const timer = setTimeout(load, SEARCH_DEBOUNCE_MS);
        return () => clearTimeout(timer);
    }, [load]);

    return (
        <main className="flex flex-col gap-6">
            <div className="flex flex-col gap-2">
                <h1 className="text-2xl font-bold text-gray-900">
                    {t("conceptsAdmin.title")}
                </h1>
                <p className="text-sm text-gray-600">{t("conceptsAdmin.intro")}</p>
            </div>

            <div className="flex flex-col gap-3">
                <input
                    type="text"
                    aria-label={t("conceptsAdmin.search")}
                    placeholder={t("conceptsAdmin.search")}
                    value={query}
                    maxLength={100}
                    onChange={(e) => {
                        setQuery(e.target.value);
                        setPage(1);
                    }}
                    className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none"
                />
                <div className="flex flex-wrap gap-2" role="radiogroup">
                    {FILTERS.map((value) => (
                        <button
                            key={value}
                            type="button"
                            role="radio"
                            aria-checked={filter === value}
                            onClick={() => {
                                setFilter(value);
                                setPage(1);
                            }}
                            className={`cursor-pointer rounded-full px-3 py-1 text-xs font-medium ${
                                filter === value
                                    ? "bg-blue-600 text-white"
                                    : "border border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
                            }`}
                        >
                            {t(FILTER_KEYS[value])}
                        </button>
                    ))}
                </div>
            </div>

            {loading && <LoadingState />}
            {!loading && failed && (
                <StatusMessage
                    variant="error"
                    message={t("conceptsAdmin.failed")}
                    onRetry={load}
                />
            )}
            {!loading && !failed && items.length === 0 && (
                <StatusMessage message={t("conceptsAdmin.empty")} />
            )}

            {!loading && !failed && items.length > 0 && (
                <>
                    <Pagination
                        page={page}
                        size={size}
                        total={total}
                        onPageChange={setPage}
                        onSizeChange={(next) => {
                            setSize(next);
                            setPage(1);
                        }}
                    />
                    <div className="flex flex-col gap-3">
                        {items.map((concept) => (
                            <Card key={concept.id} className="flex flex-col gap-2">
                                <button
                                    type="button"
                                    onClick={() =>
                                        setOpenId(openId === concept.id ? null : concept.id)
                                    }
                                    className="flex w-full cursor-pointer flex-wrap items-baseline justify-between gap-2 text-left"
                                >
                                    <span className="flex flex-wrap items-baseline gap-2">
                                        <span className="font-mono text-xs text-gray-500">
                                            #{concept.id}
                                        </span>
                                        <span className="font-medium text-gray-900">
                                            {wordsOf(concept, "ja") || t("conceptsAdmin.noWord")}
                                        </span>
                                        <span className="text-gray-700">
                                            {wordsOf(concept, "en") || t("conceptsAdmin.noWord")}
                                        </span>
                                        {(concept.gloss_ja || concept.gloss_en) && (
                                            <span className="text-xs text-gray-500">
                                                ({concept.gloss_ja ?? concept.gloss_en})
                                            </span>
                                        )}
                                    </span>
                                    <span className="flex flex-wrap gap-2 text-xs text-gray-500">
                                        {concept.terms.some((term) => term.source === "MACHINE") && (
                                            <span className="rounded-full bg-amber-50 px-2 py-0.5 text-amber-800">
                                                {t("conceptsAdmin.source.MACHINE")}
                                            </span>
                                        )}
                                        {concept.shares_word_with.length > 0 && (
                                            <span className="rounded-full bg-violet-50 px-2 py-0.5 text-violet-700">
                                                {t("conceptsAdmin.sharesWith", {
                                                    ids: concept.shares_word_with
                                                        .map((id) => `#${id}`)
                                                        .join(", "),
                                                })}
                                            </span>
                                        )}
                                        <span>
                                            {t("conceptsAdmin.questions", {
                                                count: concept.question_count,
                                            })}
                                        </span>
                                    </span>
                                </button>

                                {openId === concept.id && (
                                    <ConceptEditor
                                        conceptId={concept.id}
                                        onChanged={load}
                                        onClose={() => setOpenId(null)}
                                    />
                                )}
                            </Card>
                        ))}
                    </div>
                </>
            )}
        </main>
    );
}
