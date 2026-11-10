"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Question } from "@/types/question";
import MarkdownContent from "@/components/ui/MarkdownContent";
import ConceptChips from "@/components/ui/ConceptChips";
import { buttonClassName } from "@/components/ui/Button";
import { useLanguage } from "@/lib/i18n/LanguageContext";

/** What the preview needs: similarity results carry no tags ([56]). */
export type PreviewQuestion = Pick<Question, "id" | "question" | "answer"> & {
    concepts?: string[];
};

type QuestionPreviewModalProps = {
    question: PreviewQuestion | null;
    onClose: () => void;
};

/** Preview a related QA without leaving the page; it uses the data already loaded ([42]). */
export default function QuestionPreviewModal({
    question,
    onClose,
}: QuestionPreviewModalProps) {
    const { t } = useLanguage();

    useEffect(() => {
        if (question === null) {
            return;
        }

        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === "Escape") {
                onClose();
            }
        };

        // Freeze the page behind the dialog.
        const previousOverflow = document.body.style.overflow;
        document.body.style.overflow = "hidden";
        window.addEventListener("keydown", handleKeyDown);

        return () => {
            document.body.style.overflow = previousOverflow;
            window.removeEventListener("keydown", handleKeyDown);
        };
    }, [question, onClose]);

    if (question === null) {
        return null;
    }

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 py-6"
            role="dialog"
            aria-modal="true"
            aria-labelledby="question-preview-title"
            onClick={onClose}
        >
            <div
                className="flex max-h-full w-full max-w-2xl flex-col gap-4 overflow-y-auto rounded-lg bg-white p-6 shadow-lg"
                // Clicks inside the dialog do not close it.
                onClick={(e) => e.stopPropagation()}
            >
                <h2
                    id="question-preview-title"
                    className="text-lg font-bold text-gray-900"
                >
                    {question.question}
                </h2>

                <MarkdownContent content={question.answer} variant="full" />

                <ConceptChips concepts={question.concepts ?? []} />

                <div className="flex flex-wrap gap-2">
                    <Link
                        href={`/questions/${question.id}`}
                        className={buttonClassName("primary")}
                    >
                        {t("questionPreview.openFull")}
                    </Link>

                    <button
                        type="button"
                        onClick={onClose}
                        className={buttonClassName("secondary")}
                    >
                        {t("common.close")}
                    </button>
                </div>
            </div>
        </div>
    );
}
