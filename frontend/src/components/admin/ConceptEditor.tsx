"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import {
    ApiError,
    addConceptTerm,
    deleteConceptTerm,
    fetchAdminConcept,
    mergeConcept,
    splitConcept,
    updateConceptGloss,
    updateConceptTerm,
} from "@/lib/api";
import Button from "@/components/ui/Button";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import LoadingState from "@/components/ui/LoadingState";
import { showToast } from "@/components/ui/Toast";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { AdminConcept, ConceptTerm } from "@/types/concept";
import { ContentLanguage } from "@/types/question";

const inputClassName =
    "w-full rounded-md border border-gray-300 bg-white px-2 py-1 text-sm text-gray-900 focus:border-blue-500 focus:outline-none";

type ConceptEditorProps = {
    conceptId: number;
    onChanged: () => void;
    onClose: () => void;
};

/** Edit one concept sense: words, explanation, merge and split ([55]). */
export default function ConceptEditor({
    conceptId,
    onChanged,
    onClose,
}: ConceptEditorProps) {
    const { language, t } = useLanguage();
    const lang = language as ContentLanguage;
    const [concept, setConcept] = useState<AdminConcept | null>(null);
    const [glossJa, setGlossJa] = useState("");
    const [glossEn, setGlossEn] = useState("");
    const [newWord, setNewWord] = useState("");
    const [newWordLang, setNewWordLang] = useState<ContentLanguage>("en");
    const [newWordPreferred, setNewWordPreferred] = useState(false);
    const [mergeInto, setMergeInto] = useState("");
    const [confirmMerge, setConfirmMerge] = useState(false);
    const [selected, setSelected] = useState<Set<number>>(new Set());
    const [splitJa, setSplitJa] = useState("");
    const [splitEn, setSplitEn] = useState("");
    const [busy, setBusy] = useState(false);

    const show = useCallback((data: AdminConcept) => {
        setConcept(data);
        setGlossJa(data.gloss_ja ?? "");
        setGlossEn(data.gloss_en ?? "");
    }, []);

    useEffect(() => {
        fetchAdminConcept(conceptId, lang)
            .then(show)
            .catch((error) => {
                console.error(error);
                showToast(t("conceptsAdmin.failed"), "error");
            });
    }, [conceptId, lang, show, t]);

    // One wrapper so every edit reports, refreshes and handles 409 alike.
    const run = async (action: () => Promise<AdminConcept | void>) => {
        setBusy(true);
        try {
            const result = await action();
            if (result) show(result);
            showToast(t("conceptsAdmin.saved"));
            onChanged();
            return true;
        } catch (error) {
            const duplicate = error instanceof ApiError && error.status === 409;
            if (!duplicate) console.error(error);
            showToast(
                t(duplicate ? "conceptsAdmin.duplicate" : "conceptsAdmin.failed"),
                "error"
            );
            return false;
        } finally {
            setBusy(false);
        }
    };

    if (concept === null) {
        return <LoadingState />;
    }

    const termRow = (term: ConceptTerm) => (
        <li key={term.id} className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-medium text-gray-900">{term.term}</span>
            {term.is_preferred && (
                <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-700">
                    {t("conceptsAdmin.preferred")}
                </span>
            )}
            <span
                className={`rounded-full px-2 py-0.5 text-xs ${
                    term.source === "MACHINE"
                        ? "bg-amber-50 text-amber-800"
                        : "bg-gray-100 text-gray-600"
                }`}
            >
                {t(`conceptsAdmin.source.${term.source}`)}
            </span>
            {!term.is_preferred && (
                <Button
                    size="sm"
                    variant="secondary"
                    disabled={busy}
                    onClick={() =>
                        run(() =>
                            updateConceptTerm(term.id, { is_preferred: true }, lang)
                        )
                    }
                >
                    {t("conceptsAdmin.makePreferred")}
                </Button>
            )}
            {term.source === "MACHINE" && (
                <Button
                    size="sm"
                    variant="secondary"
                    disabled={busy}
                    onClick={() => run(() => updateConceptTerm(term.id, {}, lang))}
                >
                    {t("conceptsAdmin.confirmWord")}
                </Button>
            )}
            <Button
                size="sm"
                variant="danger"
                disabled={busy}
                onClick={() =>
                    run(async () => {
                        await deleteConceptTerm(term.id);
                        return fetchAdminConcept(concept.id, lang);
                    })
                }
            >
                {t("conceptsAdmin.delete")}
            </Button>
        </li>
    );

    const submitWord = async (e: FormEvent) => {
        e.preventDefault();
        if (!newWord.trim()) return;
        const ok = await run(() =>
            addConceptTerm(
                concept.id,
                {
                    language: newWordLang,
                    term: newWord.trim(),
                    is_preferred: newWordPreferred,
                },
                lang
            )
        );
        if (ok) setNewWord("");
    };

    const submitSplit = async (e: FormEvent) => {
        e.preventDefault();
        const terms = [
            { language: "ja" as const, term: splitJa.trim() },
            { language: "en" as const, term: splitEn.trim() },
        ].filter((item) => item.term !== "");
        if (selected.size === 0 || terms.length === 0) return;
        const ok = await run(async () => {
            await splitConcept(
                concept.id,
                { question_ids: [...selected], terms },
                lang
            );
            return fetchAdminConcept(concept.id, lang);
        });
        if (ok) {
            setSelected(new Set());
            setSplitJa("");
            setSplitEn("");
        }
    };

    const toggle = (id: number) =>
        setSelected((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });

    return (
        <div className="flex flex-col gap-5 border-t border-gray-100 pt-4">
            {(["ja", "en"] as const).map((language) => {
                const words = concept.terms.filter((term) => term.language === language);
                return (
                    <section key={language} className="flex flex-col gap-1">
                        <h3 className="text-xs font-semibold uppercase text-gray-500">
                            {language}
                        </h3>
                        {words.length === 0 ? (
                            <p className="text-sm text-gray-400">
                                {t("conceptsAdmin.noWord")}
                            </p>
                        ) : (
                            <ul className="flex flex-col gap-1">{words.map(termRow)}</ul>
                        )}
                    </section>
                );
            })}

            <form onSubmit={submitWord} className="flex flex-wrap items-end gap-2">
                <select
                    aria-label="language"
                    value={newWordLang}
                    onChange={(e) => setNewWordLang(e.target.value as ContentLanguage)}
                    className="rounded-md border border-gray-300 px-2 py-1 text-sm"
                >
                    <option value="ja">ja</option>
                    <option value="en">en</option>
                </select>
                <input
                    aria-label={t("conceptsAdmin.newWord")}
                    placeholder={t("conceptsAdmin.newWord")}
                    value={newWord}
                    maxLength={255}
                    onChange={(e) => setNewWord(e.target.value)}
                    className={`${inputClassName} max-w-60`}
                />
                <label className="flex items-center gap-1 text-xs text-gray-600">
                    <input
                        type="checkbox"
                        checked={newWordPreferred}
                        onChange={(e) => setNewWordPreferred(e.target.checked)}
                    />
                    {t("conceptsAdmin.asPreferred")}
                </label>
                <Button type="submit" size="sm" disabled={busy}>
                    {t("conceptsAdmin.addWord")}
                </Button>
            </form>

            <section className="flex flex-col gap-2">
                <h3 className="text-sm font-medium text-gray-700">
                    {t("conceptsAdmin.gloss")}
                </h3>
                <div className="grid gap-2 sm:grid-cols-2">
                    <input
                        aria-label={t("conceptsAdmin.glossJa")}
                        placeholder={t("conceptsAdmin.glossJa")}
                        value={glossJa}
                        maxLength={255}
                        onChange={(e) => setGlossJa(e.target.value)}
                        className={inputClassName}
                    />
                    <input
                        aria-label={t("conceptsAdmin.glossEn")}
                        placeholder={t("conceptsAdmin.glossEn")}
                        value={glossEn}
                        maxLength={255}
                        onChange={(e) => setGlossEn(e.target.value)}
                        className={inputClassName}
                    />
                </div>
                <Button
                    size="sm"
                    variant="secondary"
                    className="self-start"
                    disabled={busy}
                    onClick={() =>
                        run(() =>
                            updateConceptGloss(
                                concept.id,
                                { gloss_ja: glossJa || null, gloss_en: glossEn || null },
                                lang
                            )
                        )
                    }
                >
                    {t("conceptsAdmin.save")}
                </Button>
            </section>

            <form onSubmit={submitSplit} className="flex flex-col gap-2">
                <h3 className="text-sm font-medium text-gray-700">
                    {t("conceptsAdmin.split")}
                </h3>
                <p className="text-xs text-gray-500">{t("conceptsAdmin.splitHint")}</p>
                <ul className="flex max-h-64 flex-col gap-1 overflow-y-auto rounded-md border border-gray-100 p-2">
                    {(concept.questions ?? []).map((question) => (
                        <li key={question.id}>
                            <label className="flex items-start gap-2 text-sm text-gray-800">
                                <input
                                    type="checkbox"
                                    checked={selected.has(question.id)}
                                    onChange={() => toggle(question.id)}
                                />
                                <span>
                                    <span className="font-mono text-xs text-gray-500">
                                        #{question.id}
                                    </span>{" "}
                                    {question.question}
                                </span>
                            </label>
                        </li>
                    ))}
                </ul>
                <div className="grid gap-2 sm:grid-cols-2">
                    <input
                        aria-label={t("conceptsAdmin.splitWordJa")}
                        placeholder={t("conceptsAdmin.splitWordJa")}
                        value={splitJa}
                        maxLength={255}
                        onChange={(e) => setSplitJa(e.target.value)}
                        className={inputClassName}
                    />
                    <input
                        aria-label={t("conceptsAdmin.splitWordEn")}
                        placeholder={t("conceptsAdmin.splitWordEn")}
                        value={splitEn}
                        maxLength={255}
                        onChange={(e) => setSplitEn(e.target.value)}
                        className={inputClassName}
                    />
                </div>
                <Button
                    type="submit"
                    size="sm"
                    variant="secondary"
                    className="self-start"
                    disabled={
                        busy || selected.size === 0 || (!splitJa.trim() && !splitEn.trim())
                    }
                >
                    {t("conceptsAdmin.split")}
                </Button>
            </form>

            <section className="flex flex-wrap items-end gap-2">
                <input
                    aria-label={t("conceptsAdmin.mergeInto")}
                    placeholder={t("conceptsAdmin.mergeInto")}
                    inputMode="numeric"
                    value={mergeInto}
                    onChange={(e) => setMergeInto(e.target.value.replace(/\D/g, ""))}
                    className={`${inputClassName} max-w-40`}
                />
                <Button
                    size="sm"
                    variant="danger"
                    disabled={busy || mergeInto === "" || Number(mergeInto) === concept.id}
                    onClick={() => setConfirmMerge(true)}
                >
                    {t("conceptsAdmin.merge")}
                </Button>
                <Button size="sm" variant="secondary" onClick={onClose}>
                    {t("conceptsAdmin.close")}
                </Button>
            </section>

            <ConfirmDialog
                open={confirmMerge}
                title={t("conceptsAdmin.merge")}
                description={t("conceptsAdmin.mergeConfirm", { id: mergeInto })}
                confirming={busy}
                onCancel={() => setConfirmMerge(false)}
                onConfirm={async () => {
                    const ok = await run(() =>
                        mergeConcept(concept.id, Number(mergeInto), lang)
                    );
                    setConfirmMerge(false);
                    if (ok) onClose();
                }}
            />
        </div>
    );
}
