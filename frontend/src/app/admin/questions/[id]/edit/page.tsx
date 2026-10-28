"use client";

import { SyntheticEvent, useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
    fetchQuestion,
    reviewQuestion,
    translateQuestions,
    updateQuestion,
} from "@/lib/api";
import {
    ContentLanguage,
    Question,
    UpdateQuestionRequest,
} from "@/types/question";
import Card from "@/components/ui/Card";
import FormField from "@/components/ui/FormField";
import Button from "@/components/ui/Button";
import LoadingState from "@/components/ui/LoadingState";
import StatusMessage from "@/components/ui/StatusMessage";
import { showToast } from "@/components/ui/Toast";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { TranslationKey } from "@/lib/i18n/translations";

const LANGUAGES: ContentLanguage[] = ["ja", "en"];

const LANGUAGE_LABELS: Record<ContentLanguage, string> = {
    ja: "日本語",
    en: "English",
};

type TextPair = { question: string; answer: string };
type FormTexts = Record<ContentLanguage, TextPair>;

const EMPTY_TEXTS: FormTexts = {
    ja: { question: "", answer: "" },
    en: { question: "", answer: "" },
};

function textsFromQuestion(data: Question): FormTexts {
    return {
        ja: {
            question: data.texts.ja?.question ?? "",
            answer: data.texts.ja?.answer ?? "",
        },
        en: {
            question: data.texts.en?.question ?? "",
            answer: data.texts.en?.answer ?? "",
        },
    };
}

function provenanceLabelKey(
    data: Question | null,
    lang: ContentLanguage
): TranslationKey {
    const provenance = data?.texts[lang]?.provenance;

    if (provenance === "MACHINE") {
        return "admin.machineProvenance";
    }
    if (provenance === "HUMAN") {
        return "provenance.human";
    }
    if (provenance === "ORIGINAL") {
        return "provenance.original";
    }
    return "provenance.missing";
}

export default function EditQuestionPage() {
    const router = useRouter();
    const params = useParams();
    const { t } = useLanguage();
    const id = Number(params.id);
    const [loaded, setLoaded] = useState<Question | null>(null);
    const [texts, setTexts] = useState<FormTexts>(EMPTY_TEXTS);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [approving, setApproving] = useState(false);
    const [translating, setTranslating] = useState(false);
    const [errors, setErrors] = useState<Partial<Record<ContentLanguage, string>>>(
        {}
    );

    const loadQuestion = useCallback(async () => {
        setLoading(true);
        setLoadError(false);

        try {
            const data = await fetchQuestion(id);
            setLoaded(data);
            setTexts(textsFromQuestion(data));
        } catch (error) {
            console.error(error);
            setLoadError(true);
        } finally {
            setLoading(false);
        }
    }, [id]);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        loadQuestion();
    }, [loadQuestion]);

    const setField = (
        lang: ContentLanguage,
        field: keyof TextPair,
        value: string
    ) => {
        setTexts((prev) => ({
            ...prev,
            [lang]: { ...prev[lang], [field]: value },
        }));
    };

    // Only languages whose text actually changed are sent, so an untouched
    // machine translation keeps its MACHINE provenance (and stays eligible
    // for automatic regeneration).
    const buildChanges = (): UpdateQuestionRequest | null => {
        if (loaded === null) {
            return null;
        }

        const original = textsFromQuestion(loaded);
        const changes: UpdateQuestionRequest = { id };
        let changed = false;

        for (const lang of LANGUAGES) {
            const next = texts[lang];
            const prev = original[lang];

            if (
                next.question.trim() === prev.question.trim() &&
                next.answer.trim() === prev.answer.trim()
            ) {
                continue;
            }

            changes[`question_${lang}`] = next.question;
            changes[`answer_${lang}`] = next.answer;
            changed = true;
        }

        return changed ? changes : null;
    };

    const changedLanguages = (): ContentLanguage[] => {
        if (loaded === null) {
            return [];
        }

        const original = textsFromQuestion(loaded);

        return LANGUAGES.filter(
            (lang) =>
                texts[lang].question.trim() !== original[lang].question.trim() ||
                texts[lang].answer.trim() !== original[lang].answer.trim()
        );
    };

    const validate = (): Partial<Record<ContentLanguage, string>> => {
        const nextErrors: Partial<Record<ContentLanguage, string>> = {};

        for (const lang of LANGUAGES) {
            const pair = texts[lang];
            const hasQuestion = pair.question.trim() !== "";
            const hasAnswer = pair.answer.trim() !== "";

            if (hasQuestion !== hasAnswer) {
                nextErrors[lang] = t("editQuestion.pairRequired");
            }
        }

        if (
            !LANGUAGES.some(
                (lang) =>
                    texts[lang].question.trim() !== "" &&
                    texts[lang].answer.trim() !== ""
            )
        ) {
            nextErrors.ja = t("editQuestion.oneLanguageRequired");
        }

        return nextErrors;
    };

    const saveChanges = async (): Promise<boolean> => {
        const nextErrors = validate();
        setErrors(nextErrors);

        if (Object.keys(nextErrors).length > 0) {
            return false;
        }

        const changes = buildChanges();

        if (changes !== null) {
            await updateQuestion(changes);
        }

        return true;
    };

    const handleSubmit = async (e: SyntheticEvent<HTMLFormElement>) => {
        e.preventDefault();
        setSubmitting(true);

        try {
            if (await saveChanges()) {
                showToast(t("editQuestion.updated"));
                router.push("/admin/questions");
                return;
            }
        } catch (error) {
            console.error(error);
            showToast(t("editQuestion.updateFailed"), "error");
        }
        setSubmitting(false);
    };

    const handleSaveAndApprove = async () => {
        const nextErrors = validate();
        setErrors(nextErrors);

        if (Object.keys(nextErrors).length > 0) {
            return;
        }

        setApproving(true);

        try {
            // EDIT_APPROVE stores the teacher's correction as a before/after
            // diff in the review history; a separate PUT followed by APPROVE
            // would record the edit as a no-op.
            const changed = changedLanguages();

            if (changed.length === 0) {
                await reviewQuestion(id, { action: "APPROVE" });
            } else {
                // Machine-translated languages first: approving the original
                // regenerates MACHINE counterparts, which would discard a
                // correction the teacher just made in the other language.
                const ordered = [...changed].sort(
                    (a, b) =>
                        (loaded?.texts[a]?.provenance === "MACHINE" ? 0 : 1) -
                        (loaded?.texts[b]?.provenance === "MACHINE" ? 0 : 1)
                );

                for (const lang of ordered) {
                    await reviewQuestion(id, {
                        action: "EDIT_APPROVE",
                        language: lang,
                        question: texts[lang].question,
                        answer: texts[lang].answer,
                    });
                }
            }

            showToast(t("editQuestion.savedAndApproved"));
            router.push("/admin/questions");
            return;
        } catch (error) {
            console.error(error);
            showToast(t("editQuestion.actionFailed"), "error");
        }
        setApproving(false);
    };

    const handleTranslate = async () => {
        setTranslating(true);

        try {
            await translateQuestions([id]);
            await loadQuestion();
            showToast(t("editQuestion.translated"));
        } catch (error) {
            console.error(error);
            showToast(t("editQuestion.translateFailed"), "error");
        } finally {
            setTranslating(false);
        }
    };

    if (loading) {
        return <LoadingState />;
    }

    if (loadError) {
        return (
            <StatusMessage
                variant="error"
                message={t("editQuestion.fetchFailed")}
                onRetry={loadQuestion}
            />
        );
    }

    const busy = submitting || approving || translating;
    const hasMissingLanguage = LANGUAGES.some(
        (lang) => loaded?.texts[lang] === undefined
    );

    return (
        <main className="flex flex-col gap-6">
            <h1 className="text-2xl font-bold text-gray-900">{t("editQuestion.title")}</h1>

            <Card>
                <form
                    onSubmit={handleSubmit}
                    noValidate
                    className="flex flex-col gap-6"
                >
                    {LANGUAGES.map((lang) => (
                        <fieldset key={lang} className="flex flex-col gap-4">
                            <legend className="flex items-center gap-2 text-sm font-semibold text-gray-900">
                                {LANGUAGE_LABELS[lang]}
                                <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                                    {t(provenanceLabelKey(loaded, lang))}
                                </span>
                            </legend>

                            {errors[lang] && (
                                <p className="text-sm text-red-600">
                                    {errors[lang]}
                                </p>
                            )}

                            <FormField
                                id={`question-${lang}`}
                                label={t("form.questionLabel")}
                                value={texts[lang].question}
                                onChange={(e) =>
                                    setField(lang, "question", e.target.value)
                                }
                                rows={3}
                            />

                            <FormField
                                id={`answer-${lang}`}
                                label={t("form.answerLabel")}
                                value={texts[lang].answer}
                                onChange={(e) =>
                                    setField(lang, "answer", e.target.value)
                                }
                                rows={6}
                            />
                        </fieldset>
                    ))}

                    <div className="flex flex-wrap gap-2">
                        <Button type="submit" disabled={busy}>
                            {submitting ? t("common.saving") : t("common.save")}
                        </Button>

                        <Button
                            type="button"
                            variant="secondary"
                            disabled={busy}
                            onClick={handleSaveAndApprove}
                        >
                            {approving
                                ? t("common.processing")
                                : t("editQuestion.saveAndApprove")}
                        </Button>

                        {hasMissingLanguage && (
                            <Button
                                type="button"
                                variant="secondary"
                                disabled={busy}
                                onClick={handleTranslate}
                            >
                                {translating
                                    ? t("editQuestion.translating")
                                    : t("editQuestion.translateMissing")}
                            </Button>
                        )}
                    </div>
                </form>
            </Card>
        </main>
    );
}
