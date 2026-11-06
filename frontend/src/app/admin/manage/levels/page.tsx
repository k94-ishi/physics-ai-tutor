"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchQuestions, updateQuestion } from "@/lib/api";
import { Question } from "@/types/question";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { TranslationKey } from "@/lib/i18n/translations";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import LoadingState from "@/components/ui/LoadingState";
import MarkdownContent from "@/components/ui/MarkdownContent";
import StatusMessage from "@/components/ui/StatusMessage";
import QuestionIdBadge from "@/components/ui/QuestionIdBadge";
import { showToast } from "@/components/ui/Toast";

export const LEVEL_FIELDS = ["physics_level", "math_level"] as const;

export type LevelField = (typeof LEVEL_FIELDS)[number];
export type MyRating = Partial<Record<LevelField, number>>;
export type MyRatings = Record<number, MyRating>;

type Filter = "all" | "sample" | "mine" | "unrated" | "disagree" | "modelUnrated";

const LEVELS = [0, 1, 2, 3, 4];
const PAGE_SIZE = 120;
// Own ratings live in the browser only; see the intro text on the page.
export const STORAGE_KEY = "levelsReview.myRatings";
export const SAMPLE_KEY = "levelsReview.sampleIds";
export const SAMPLE_SIZE = 30;

export type AxisAgreement = {
    n: number;
    exact: number;
    within1: number;
    meanOffset: number;
};

/** Agreement of the LLM's ratings with mine, per axis. */
export function agreementByField(
    questions: Question[],
    mine: MyRatings
): Record<LevelField, AxisAgreement> {
    const result = {} as Record<LevelField, AxisAgreement>;

    for (const field of LEVEL_FIELDS) {
        let n = 0;
        let exact = 0;
        let within1 = 0;
        let offsetSum = 0;

        for (const question of questions) {
            const own = mine[question.id]?.[field];
            const model = question[field];
            if (own === undefined || model === null) continue;
            n += 1;
            const diff = model - own;
            if (diff === 0) exact += 1;
            if (Math.abs(diff) <= 1) within1 += 1;
            offsetSum += diff;
        }

        result[field] = { n, exact, within1, meanOffset: n ? offsetSum / n : 0 };
    }

    return result;
}

function disagrees(question: Question, own: MyRating | undefined): boolean {
    if (!own) return false;
    return LEVEL_FIELDS.some(
        (field) =>
            own[field] !== undefined &&
            question[field] !== null &&
            own[field] !== question[field]
    );
}

function loadJson<T>(key: string, fallback: T): T {
    if (typeof window === "undefined") return fallback;
    try {
        return JSON.parse(window.localStorage.getItem(key) ?? "") ?? fallback;
    } catch {
        return fallback;
    }
}

/** A fixed random sample so the evaluation covers the corpus, not the top of the list. */
export function pickSample(ids: number[], size: number): number[] {
    const pool = [...ids];
    for (let i = pool.length - 1; i > 0; i -= 1) {
        const j = Math.floor(Math.random() * (i + 1));
        [pool[i], pool[j]] = [pool[j], pool[i]];
    }
    return pool.slice(0, size).sort((a, b) => a - b);
}

async function fetchAllApproved(lang: "ja" | "en"): Promise<Question[]> {
    const items: Question[] = [];
    let page = 1;

    // Small corpus: walk every page once instead of paginating the table.
    for (;;) {
        const data = await fetchQuestions({
            page,
            size: PAGE_SIZE,
            status: "APPROVED",
            lang,
        });
        items.push(...data.items);
        if (items.length >= data.total || data.items.length === 0) break;
        page += 1;
    }

    return items;
}

function RubricTable() {
    const { t } = useLanguage();

    return (
        <table className="w-full text-xs leading-snug">
            <thead>
                <tr className="text-left text-gray-500">
                    <th className="w-14 py-1 pr-2">{t("levelsReview.rubricLevel")}</th>
                    <th className="py-1 pr-2">{t("levelsReview.rubricPhysics")}</th>
                    <th className="py-1">{t("levelsReview.rubricMath")}</th>
                </tr>
            </thead>
            <tbody>
                {LEVELS.map((level) => (
                    <tr key={level} className="border-t border-gray-100 align-top">
                        <td className="py-1 pr-2 font-semibold">{level}</td>
                        <td className="py-1 pr-2">
                            {t(`levelsReview.physicsDesc${level}` as TranslationKey)}
                        </td>
                        <td className="py-1">
                            {t(`levelsReview.mathDesc${level}` as TranslationKey)}
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    );
}

function SummaryTable({
    questions,
    mine,
}: {
    questions: Question[];
    mine: MyRatings;
}) {
    const { t } = useLanguage();
    const stats = useMemo(() => agreementByField(questions, mine), [questions, mine]);
    const total = LEVEL_FIELDS.reduce((sum, field) => sum + stats[field].n, 0);

    const fieldLabel = (field: LevelField) =>
        t(field === "physics_level" ? "levelsReview.physics" : "levelsReview.math");

    const pct = (part: number, n: number) => (n ? `${Math.round((100 * part) / n)}%` : "-");

    const copy = async () => {
        const header = `| axis | n | exact | within ±1 | mean offset (LLM − me) |\n| --- | --- | --- | --- | --- |`;
        const rows = LEVEL_FIELDS.map((field) => {
            const s = stats[field];
            return `| ${field} | ${s.n} | ${pct(s.exact, s.n)} | ${pct(s.within1, s.n)} | ${s.meanOffset.toFixed(2)} |`;
        });
        await navigator.clipboard.writeText([header, ...rows].join("\n"));
        showToast(t("levelsReview.copied"));
    };

    if (total === 0) {
        return <p className="text-sm text-gray-500">{t("levelsReview.summaryNone")}</p>;
    }

    return (
        <div className="flex flex-col gap-2">
            <table className="w-full text-sm">
                <thead>
                    <tr className="text-left text-gray-500">
                        <th className="py-1 pr-2" />
                        <th className="py-1 pr-2">{t("levelsReview.summaryN")}</th>
                        <th className="py-1 pr-2">{t("levelsReview.summaryExact")}</th>
                        <th className="py-1 pr-2">{t("levelsReview.summaryWithin1")}</th>
                        <th className="py-1">{t("levelsReview.summaryMean")}</th>
                    </tr>
                </thead>
                <tbody>
                    {LEVEL_FIELDS.map((field) => (
                        <tr key={field} className="border-t border-gray-100">
                            <td className="py-1 pr-2 font-medium">{fieldLabel(field)}</td>
                            <td className="py-1 pr-2">{stats[field].n}</td>
                            <td className="py-1 pr-2">{pct(stats[field].exact, stats[field].n)}</td>
                            <td className="py-1 pr-2">{pct(stats[field].within1, stats[field].n)}</td>
                            <td className="py-1">{stats[field].meanOffset.toFixed(2)}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
            <div>
                <Button variant="secondary" size="sm" onClick={copy}>
                    {t("levelsReview.copySummary")}
                </Button>
            </div>
        </div>
    );
}

function LevelCell({
    value,
    own,
    hidden,
}: {
    value: number | null;
    own: number | undefined;
    hidden: boolean;
}) {
    const { t } = useLanguage();

    if (hidden) return <span className="text-gray-400">{t("levelsReview.hidden")}</span>;
    if (value === null) return <span className="text-gray-400">{t("levelsReview.blank")}</span>;

    const tone =
        own === undefined || own === value
            ? "text-gray-900"
            : Math.abs(own - value) === 1
              ? "text-amber-700 font-semibold"
              : "text-red-700 font-semibold";

    return <span className={tone}>{value}</span>;
}

function LevelSelect({
    value,
    onChange,
    label,
}: {
    value: number | undefined;
    onChange: (next: number | undefined) => void;
    label: string;
}) {
    return (
        <select
            aria-label={label}
            value={value === undefined ? "" : String(value)}
            onChange={(e) => onChange(e.target.value === "" ? undefined : Number(e.target.value))}
            className="w-12 rounded border border-gray-300 bg-white px-1 py-0.5 text-sm"
        >
            <option value="" />
            {LEVELS.map((level) => (
                <option key={level} value={level}>
                    {level}
                </option>
            ))}
        </select>
    );
}

function QuestionRow({
    question,
    own,
    hideModel,
    onRate,
    onSaved,
}: {
    question: Question;
    own: MyRating | undefined;
    hideModel: boolean;
    onRate: (id: number, field: LevelField, value: number | undefined) => void;
    onSaved: (updated: Question) => void;
}) {
    const { t } = useLanguage();
    const [open, setOpen] = useState(false);
    const [saving, setSaving] = useState(false);
    const hasOwn = own !== undefined && LEVEL_FIELDS.some((f) => own[f] !== undefined);

    const save = async () => {
        if (!own) return;
        setSaving(true);
        try {
            const updated = await updateQuestion({ id: question.id, ...own });
            onSaved(updated);
            showToast(t("levelsReview.applied", { id: question.id }));
        } catch (error) {
            console.error(error);
            showToast(t("levelsReview.applyFailed"));
        } finally {
            setSaving(false);
        }
    };

    const fieldLabel = (field: LevelField) =>
        `${t("levelsReview.colMine")} ${t(
            field === "physics_level" ? "levelsReview.physics" : "levelsReview.math"
        )} #${question.id}`;

    return (
        <>
            <tr className="border-t border-gray-200 align-top">
                <td className="py-2 pr-2">
                    <div className="flex items-start gap-2">
                        <QuestionIdBadge id={question.id} />
                        <button
                            type="button"
                            onClick={() => setOpen((v) => !v)}
                            className="text-left text-gray-900 hover:underline"
                        >
                            {question.question}
                        </button>
                    </div>
                </td>
                {LEVEL_FIELDS.map((field) => (
                    <td key={field} className="px-1 py-2 text-center">
                        <LevelCell value={question[field]} own={own?.[field]} hidden={hideModel} />
                    </td>
                ))}
                {LEVEL_FIELDS.map((field) => (
                    <td key={`mine-${field}`} className="px-1 py-2 text-center">
                        <LevelSelect
                            value={own?.[field]}
                            onChange={(next) => onRate(question.id, field, next)}
                            label={fieldLabel(field)}
                        />
                    </td>
                ))}
                <td className="py-2 pl-2">
                    <Button
                        variant="secondary"
                        size="sm"
                        disabled={!hasOwn || saving}
                        onClick={save}
                    >
                        {t("levelsReview.apply")}
                    </Button>
                </td>
            </tr>
            {open && (
                <tr className="bg-gray-50">
                    <td colSpan={6} className="p-3">
                        <div className="flex flex-col gap-3 text-sm">
                            <div>
                                <div className="mb-1 text-xs font-semibold text-gray-500">
                                    {t("levelsReview.q")}
                                </div>
                                <MarkdownContent content={question.question} />
                            </div>
                            <div>
                                <div className="mb-1 text-xs font-semibold text-gray-500">
                                    {t("levelsReview.a")}
                                </div>
                                <MarkdownContent content={question.answer} />
                            </div>
                            <div className="text-gray-700">
                                <span className="font-semibold">{t("levelsReview.concepts")}: </span>
                                {question.concepts.length
                                    ? question.concepts.join(" / ")
                                    : t("levelsReview.noConcepts")}
                            </div>
                            <div>
                                <Link
                                    href={`/admin/questions/${question.id}/edit`}
                                    className="text-blue-600 hover:underline"
                                >
                                    {t("levelsReview.editLink")}
                                </Link>
                            </div>
                        </div>
                    </td>
                </tr>
            )}
        </>
    );
}

export default function AdminLevelsPage() {
    const { language, t } = useLanguage();
    const [questions, setQuestions] = useState<Question[]>([]);
    const [mine, setMine] = useState<MyRatings>({});
    const [sampleIds, setSampleIds] = useState<number[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);
    const [showRubric, setShowRubric] = useState(true);
    const [hideModel, setHideModel] = useState(false);
    const [filter, setFilter] = useState<Filter>("all");
    const [keyword, setKeyword] = useState("");

    const load = useCallback(async () => {
        setLoading(true);
        setError(false);
        try {
            setQuestions(await fetchAllApproved(language));
        } catch (err) {
            console.error(err);
            setError(true);
        } finally {
            setLoading(false);
        }
    }, [language]);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setMine(loadJson<MyRatings>(STORAGE_KEY, {}));
        setSampleIds(loadJson<number[]>(SAMPLE_KEY, []));
        load();
    }, [load]);

    const rate = (id: number, field: LevelField, value: number | undefined) => {
        setMine((prev) => {
            const next = { ...prev, [id]: { ...prev[id], [field]: value } };
            if (value === undefined) delete next[id][field];
            if (!LEVEL_FIELDS.some((f) => next[id][f] !== undefined)) delete next[id];
            window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
            return next;
        });
    };

    const drawSample = () => {
        const ids = pickSample(
            questions.map((q) => q.id),
            SAMPLE_SIZE
        );
        window.localStorage.setItem(SAMPLE_KEY, JSON.stringify(ids));
        setSampleIds(ids);
        setFilter("sample");
    };

    const clearSample = () => {
        window.localStorage.removeItem(SAMPLE_KEY);
        setSampleIds([]);
        if (filter === "sample") setFilter("all");
    };

    const onSaved = (updated: Question) => {
        setQuestions((prev) => prev.map((q) => (q.id === updated.id ? { ...q, ...updated } : q)));
    };

    const visible = useMemo(() => {
        const needle = keyword.trim().toLowerCase();
        return questions.filter((q) => {
            const own = mine[q.id];
            const rated = own !== undefined;
            if (filter === "sample" && !sampleIds.includes(q.id)) return false;
            if (filter === "mine" && !rated) return false;
            if (filter === "unrated" && rated) return false;
            if (filter === "disagree" && !disagrees(q, own)) return false;
            if (filter === "modelUnrated" && LEVEL_FIELDS.some((f) => q[f] !== null)) return false;
            return !needle || q.question.toLowerCase().includes(needle);
        });
    }, [questions, mine, filter, keyword, sampleIds]);

    if (loading) return <LoadingState />;
    if (error) {
        return (
            <StatusMessage variant="error" message={t("levelsReview.loadFailed")} onRetry={load} />
        );
    }

    const filters: Filter[] = ["all", "sample", "mine", "unrated", "disagree", "modelUnrated"];
    const filterKey: Record<Filter, TranslationKey> = {
        all: "levelsReview.filterAll",
        sample: "levelsReview.filterSample",
        mine: "levelsReview.filterMine",
        unrated: "levelsReview.filterUnrated",
        disagree: "levelsReview.filterDisagree",
        modelUnrated: "levelsReview.filterModelUnrated",
    };

    return (
        <main className="flex flex-col gap-6">
            <div className="flex flex-col gap-2">
                <h1 className="text-2xl font-bold text-gray-900">{t("levelsReview.title")}</h1>
                <p className="text-sm text-gray-600">{t("levelsReview.intro")}</p>
            </div>

            {/* Stays at the top while scrolling so the rubric is always in view. */}
            <Card className="sticky top-0 z-30 flex flex-col gap-2 bg-white/95 backdrop-blur">
                <div>
                    <Button variant="secondary" size="sm" onClick={() => setShowRubric((v) => !v)}>
                        {t(showRubric ? "levelsReview.rubricHide" : "levelsReview.rubricShow")}
                    </Button>
                </div>
                {showRubric && <RubricTable />}
            </Card>

            <Card className="flex flex-col gap-2">
                <h2 className="text-base font-semibold text-gray-900">
                    {t("levelsReview.summaryTitle")}
                </h2>
                <SummaryTable questions={questions} mine={mine} />
            </Card>

            <div className="flex flex-wrap items-center gap-4 text-sm text-gray-700">
                <label className="flex items-center gap-2">
                    <input
                        type="checkbox"
                        checked={hideModel}
                        onChange={(e) => setHideModel(e.target.checked)}
                    />
                    {t("levelsReview.hideModel")}
                </label>
                <label className="flex items-center gap-2">
                    {t("levelsReview.filterLabel")}
                    <select
                        value={filter}
                        onChange={(e) => setFilter(e.target.value as Filter)}
                        className="rounded-md border border-gray-300 bg-white px-2 py-1 text-sm"
                    >
                        {filters.map((f) => (
                            <option key={f} value={f}>
                                {t(filterKey[f])}
                            </option>
                        ))}
                    </select>
                </label>
                <input
                    type="search"
                    value={keyword}
                    onChange={(e) => setKeyword(e.target.value)}
                    placeholder={t("levelsReview.keywordPlaceholder")}
                    className="rounded-md border border-gray-300 px-2 py-1 text-sm"
                />
                <span className="text-gray-500">
                    {t("levelsReview.count", { shown: visible.length, total: questions.length })}
                </span>
                <Button variant="secondary" size="sm" onClick={drawSample} title={t("levelsReview.sampleHint", { n: SAMPLE_SIZE })}>
                    {t("levelsReview.sample", { n: SAMPLE_SIZE })}
                </Button>
                {sampleIds.length > 0 && (
                    <Button variant="secondary" size="sm" onClick={clearSample}>
                        {t("levelsReview.clearSample")}
                    </Button>
                )}
            </div>

            {visible.length === 0 ? (
                <p className="text-sm text-gray-500">{t("levelsReview.empty")}</p>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="text-left text-xs text-gray-500">
                                <th rowSpan={2} className="py-1 pr-2 align-bottom">
                                    {t("levelsReview.colQuestion")}
                                </th>
                                <th colSpan={2} className="px-1 py-1 text-center">
                                    {t("levelsReview.colModel")}
                                </th>
                                <th colSpan={2} className="px-1 py-1 text-center">
                                    {t("levelsReview.colMine")}
                                </th>
                                <th rowSpan={2} />
                            </tr>
                            <tr className="text-center text-xs text-gray-500">
                                {[0, 1].map((group) =>
                                    LEVEL_FIELDS.map((field) => (
                                        <th key={`${group}-${field}`} className="px-1 py-1 font-normal">
                                            {t(field === "physics_level" ? "levelsReview.physics" : "levelsReview.math")}
                                        </th>
                                    ))
                                )}
                            </tr>
                        </thead>
                        <tbody>
                            {visible.map((question) => (
                                <QuestionRow
                                    key={question.id}
                                    question={question}
                                    own={mine[question.id]}
                                    hideModel={hideModel}
                                    onRate={rate}
                                    onSaved={onSaved}
                                />
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </main>
    );
}
