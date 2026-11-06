"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Question } from "@/types/question";
import MarkdownContent from "@/components/ui/MarkdownContent";
import ConceptChips from "@/components/ui/ConceptChips";
import { buttonClassName } from "@/components/ui/Button";
import { useLanguage } from "@/lib/i18n/LanguageContext";

type QuestionPreviewModalProps = {
    question: Question | null;
    onClose: () => void;
};

/**
 * 関連QAを開いても今読んでいるページを失わないためのプレビュー([42])。
 * 前提にあたる質問をのぞいてから戻る、という動きがこのアプリの肝なので、
 * 一覧は全文を持っている関連QAをそのまま表示し、追加の取得はしない。
 */
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

        // 背面のページがスクロールしないよう固定する。
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
                // 中身のクリックで閉じないようにする。
                onClick={(e) => e.stopPropagation()}
            >
                <h2
                    id="question-preview-title"
                    className="text-lg font-bold text-gray-900"
                >
                    {question.question}
                </h2>

                <MarkdownContent content={question.answer} variant="full" />

                <ConceptChips concepts={question.concepts} />

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
