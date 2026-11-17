"use client";

import { FormEvent } from "react";
import Button from "@/components/ui/Button";
import SelectField from "@/components/ui/SelectField";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import {
    AiVerdictFilter,
    QuestionSort,
    QuestionStatus,
} from "@/types/question";

export type QueueMode = "ai" | "keyword";
export type ConceptFilter = "" | "extracted" | "unextracted";

function modeButtonClassName(active: boolean): string {
    return `rounded-md px-4 py-2 text-sm font-medium transition-colors ${
        active
            ? "bg-blue-600 text-white"
            : "border border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
    }`;
}

const inputClassName =
    "w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

type AdminQueueFiltersProps = {
    mode: QueueMode;
    onModeChange: (mode: QueueMode) => void;
    status: QuestionStatus | "";
    conceptFilter: ConceptFilter;
    sort: QuestionSort | "";
    aiVerdict: AiVerdictFilter | "";
    /** Writes URL-backed list state, as useQueryState's setter does. */
    onQueryChange: (patch: Record<string, string>) => void;
    keywordInput: string;
    onKeywordInput: (value: string) => void;
    similarityInput: string;
    onSimilarityInput: (value: string) => void;
    similarityLoading: boolean;
    onSimilaritySubmit: (e: FormEvent<HTMLFormElement>) => void;
};

/** Mode tabs, list filters and the two search inputs of the admin queue ([63]). */
export default function AdminQueueFilters({
    mode,
    onModeChange,
    status,
    conceptFilter,
    sort,
    aiVerdict,
    onQueryChange,
    keywordInput,
    onKeywordInput,
    similarityInput,
    onSimilarityInput,
    similarityLoading,
    onSimilaritySubmit,
}: AdminQueueFiltersProps) {
    const { t } = useLanguage();

    return (
        <>
            <div className="flex flex-wrap items-end gap-4">
                <div className="flex gap-2">
                    <button
                        type="button"
                        className={modeButtonClassName(mode === "ai")}
                        onClick={() => onModeChange("ai")}
                    >
                        {t("admin.similaritySearchMode")}
                    </button>

                    <button
                        type="button"
                        className={modeButtonClassName(mode === "keyword")}
                        onClick={() => onModeChange("keyword")}
                    >
                        {t("common.keywordSearch")}
                    </button>
                </div>

                {mode === "keyword" && (
                    <>
                        <div className="w-56">
                            <SelectField
                                id="status-filter"
                                label={t("admin.statusFilterLabel")}
                                value={status}
                                onChange={(e) =>
                                    onQueryChange({
                                        status: e.target.value,
                                        page: "1",
                                    })
                                }
                                options={[
                                    { value: "", label: t("common.all") },
                                    {
                                        value: "UNREVIEWED",
                                        label: t("admin.status.unreviewed"),
                                    },
                                    {
                                        value: "APPROVED",
                                        label: t("admin.status.approved"),
                                    },
                                    {
                                        value: "REJECTED",
                                        label: t("admin.status.rejected"),
                                    },
                                ]}
                            />
                        </div>

                        <div className="w-56">
                            <SelectField
                                id="concept-filter"
                                label={t("admin.conceptFilterLabel")}
                                value={conceptFilter}
                                onChange={(e) =>
                                    onQueryChange({
                                        conceptFilter: e.target.value,
                                    })
                                }
                                options={[
                                    { value: "", label: t("common.all") },
                                    {
                                        value: "extracted",
                                        label: t("admin.conceptExtracted"),
                                    },
                                    {
                                        value: "unextracted",
                                        label: t("admin.conceptUnextracted"),
                                    },
                                ]}
                            />
                        </div>

                        <div className="w-56">
                            <SelectField
                                id="ai-verdict-filter"
                                label={t("admin.aiVerdictFilterLabel")}
                                value={aiVerdict}
                                onChange={(e) =>
                                    onQueryChange({
                                        aiVerdict: e.target.value,
                                        page: "1",
                                    })
                                }
                                options={[
                                    { value: "", label: t("common.all") },
                                    {
                                        value: "REJECT",
                                        label: t("admin.aiVerdictReject"),
                                    },
                                    {
                                        value: "EDIT",
                                        label: t("admin.aiVerdictEdit"),
                                    },
                                    {
                                        value: "APPROVE",
                                        label: t("admin.aiVerdictApprove"),
                                    },
                                    {
                                        value: "NONE",
                                        label: t("admin.aiVerdictNone"),
                                    },
                                ]}
                            />
                        </div>

                        <div className="w-56">
                            <SelectField
                                id="sort-order"
                                label={t("admin.sortLabel")}
                                value={sort}
                                onChange={(e) =>
                                    onQueryChange({
                                        sort: e.target.value,
                                        page: "1",
                                    })
                                }
                                options={[
                                    {
                                        value: "",
                                        label: t("admin.sortDefault"),
                                    },
                                    {
                                        value: "oldest",
                                        label: t("admin.sortOldest"),
                                    },
                                    {
                                        value: "ai_confidence",
                                        label: t("admin.sortAiConfidence"),
                                    },
                                    {
                                        value: "asked_count",
                                        label: t("admin.sortAskedCount"),
                                    },
                                ]}
                            />
                        </div>
                    </>
                )}
            </div>

            {mode === "ai" ? (
                <form onSubmit={onSimilaritySubmit} className="flex gap-2">
                    <input
                        type="text"
                        value={similarityInput}
                        onChange={(e) => onSimilarityInput(e.target.value)}
                        placeholder={t("questionSearch.placeholder")}
                        className={inputClassName}
                    />

                    <Button
                        type="submit"
                        disabled={similarityLoading || !similarityInput.trim()}
                        className="shrink-0"
                    >
                        {t("common.search")}
                    </Button>
                </form>
            ) : (
                <input
                    type="text"
                    value={keywordInput}
                    onChange={(e) => onKeywordInput(e.target.value)}
                    placeholder={t("admin.keywordPlaceholder")}
                    className={inputClassName}
                />
            )}
        </>
    );
}
