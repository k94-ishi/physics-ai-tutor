"use client";

import Link from "next/link";
import { AiVerdict, Question, QuestionStatus } from "@/types/question";
import Card from "@/components/ui/Card";
import Button, { buttonClassName } from "@/components/ui/Button";
import { reasonLabelKey } from "@/components/ui/ReviewReasonDialog";
import MarkdownContent from "@/components/ui/MarkdownContent";
import ReferencedQuestions from "@/components/ui/ReferencedQuestions";
import { isAiReviewable } from "@/lib/aiReviewEligibility";
import QuestionIdBadge from "@/components/ui/QuestionIdBadge";
import { TranslationKey } from "@/lib/i18n/translations";
import { useLanguage } from "@/lib/i18n/LanguageContext";

const AI_VERDICT_SHORT_KEYS: Record<AiVerdict, TranslationKey> = {
    APPROVE: "admin.aiShortApprove",
    EDIT: "admin.aiShortEdit",
    REJECT: "admin.aiShortReject",
};

const AI_VERDICT_BADGE_CLASSES: Record<AiVerdict | "UNPARSED", string> = {
    APPROVE: "bg-green-50 text-green-700",
    EDIT: "bg-yellow-50 text-yellow-800",
    REJECT: "bg-red-50 text-red-700",
    UNPARSED: "bg-gray-100 text-gray-500",
};

const STATUS_LABEL_KEYS: Record<QuestionStatus, TranslationKey> = {
    UNREVIEWED: "admin.status.unreviewed",
    APPROVED: "admin.status.approved",
    REJECTED: "admin.status.rejected",
};

const STATUS_BADGE_CLASSES: Record<QuestionStatus, string> = {
    UNREVIEWED: "bg-yellow-50 text-yellow-700",
    APPROVED: "bg-green-50 text-green-700",
    REJECTED: "bg-red-50 text-red-700",
};

export type ExtractionStatus = "processing" | "done" | "error";
export type ReviewActionState = {
    action: "APPROVE" | "REJECT";
    state: "processing" | "error";
};

type AdminQuestionCardProps = {
    question: Question;
    isSelected: boolean;
    extraction: ExtractionStatus | undefined;
    review: ReviewActionState | undefined;
    aiReviewing: boolean;
    /** A whole-queue AI review run is starting or running. */
    aiBusy: boolean;
    /** The tag the queue is filtered by, highlighted on the card. */
    activeConcept: string;
    onToggleSelected: () => void;
    onFilterConcept: (concept: string) => void;
    onApprove: () => void;
    onReject: () => void;
    onAiReview: () => void;
    onExtract: () => void;
    onDelete: () => void;
};

/** One question in the admin review queue ([63]). */
export default function AdminQuestionCard({
    question,
    isSelected,
    extraction,
    review,
    aiReviewing,
    aiBusy,
    activeConcept,
    onToggleSelected,
    onFilterConcept,
    onApprove,
    onReject,
    onAiReview,
    onExtract,
    onDelete,
}: AdminQuestionCardProps) {
    const { t } = useLanguage();
    const hasConcepts = question.concepts.length > 0;

    return (
        <Card
            onClick={() => onToggleSelected()}
            className={`flex cursor-pointer items-start gap-3 transition-colors ${
                isSelected
                    ? "border-blue-400 bg-blue-50/40"
                    : "hover:border-gray-300"
            }`}
        >
            <input
                type="checkbox"
                checked={isSelected}
                onChange={() => onToggleSelected()}
                onClick={(e) => e.stopPropagation()}
                className="mt-1 shrink-0"
                aria-label={t("admin.selectQuestion", {
                    question: question.question,
                })}
            />

            <div className="flex min-w-0 flex-1 flex-col gap-2">
                <div className="flex flex-wrap items-center gap-2">
                    <QuestionIdBadge id={question.id} />

                    <span
                        className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE_CLASSES[question.status]}`}
                    >
                        {t(STATUS_LABEL_KEYS[question.status])}
                    </span>

                    {question.source === "RAG_RESULT" && (
                        <span className="shrink-0 rounded-full bg-purple-50 px-2 py-0.5 text-xs font-medium text-purple-700">
                            {t("admin.ragGenerated")}
                        </span>
                    )}

                    {(["ja", "en"] as const).map((lang) => {
                        const text = question.texts[lang];
                        return (
                            <span
                                key={lang}
                                className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                                    text
                                        ? "bg-gray-100 text-gray-700"
                                        : "bg-gray-50 text-gray-400 line-through"
                                }`}
                                title={
                                    text?.provenance === "MACHINE"
                                        ? t("admin.machineProvenance")
                                        : undefined
                                }
                            >
                                {lang.toUpperCase()}
                                {text?.provenance === "MACHINE" && "*"}
                            </span>
                        );
                    })}

                    <span
                        className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                            hasConcepts
                                ? "bg-blue-50 text-blue-700"
                                : "bg-gray-100 text-gray-500"
                        }`}
                    >
                        {hasConcepts
                            ? t("admin.conceptsExtractedCount", {
                                  count: question.concepts.length,
                              })
                            : t("admin.conceptsNotExtracted")}
                    </span>

                    {extraction === "processing" && (
                        <span className="shrink-0 animate-pulse rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                            {t("admin.extractionProcessing")}
                        </span>
                    )}

                    {extraction === "done" && (
                        <span className="shrink-0 rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
                            {t("admin.extractionDone")}
                        </span>
                    )}

                    {extraction === "error" && (
                        <span className="shrink-0 rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
                            {t("admin.extractionFailed")}
                        </span>
                    )}

                    {question.ai_review && (
                        <span
                            className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                                AI_VERDICT_BADGE_CLASSES[
                                    question.ai_review.verdict ?? "UNPARSED"
                                ]
                            }`}
                            title={question.ai_review.rationale ?? undefined}
                        >
                            AI:{" "}
                            {question.ai_review.verdict
                                ? t(
                                      AI_VERDICT_SHORT_KEYS[
                                          question.ai_review.verdict
                                      ],
                                  )
                                : t("admin.aiShortUnparsed")}
                            {question.ai_review.confidence !== null &&
                                ` ${Math.round(
                                    question.ai_review.confidence * 100,
                                )}%`}
                            {question.ai_review.reasons[0] &&
                                ` · ${t(
                                    reasonLabelKey(
                                        question.ai_review.reasons[0],
                                    ),
                                )}`}
                        </span>
                    )}

                    {question.physics_level !== null && (
                        <span
                            className="shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700"
                            title={t("levels.badgeTitle", {
                                p: question.physics_level,
                                m: question.math_level ?? "-",
                            })}
                        >
                            {t("levels.badge", {
                                p: question.physics_level,
                                m: question.math_level ?? "-",
                            })}
                        </span>
                    )}

                    {aiReviewing && (
                        <span className="shrink-0 animate-pulse rounded-full bg-purple-50 px-2 py-0.5 text-xs font-medium text-purple-700">
                            {t("admin.aiReviewProcessing")}
                        </span>
                    )}

                    {review?.state === "processing" && (
                        <span className="shrink-0 animate-pulse rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                            {review.action === "APPROVE"
                                ? t("admin.approving")
                                : t("admin.rejecting")}
                        </span>
                    )}

                    {review?.state === "error" && (
                        <span className="shrink-0 rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
                            {review.action === "APPROVE"
                                ? t("admin.approveFailed")
                                : t("admin.rejectFailed")}
                        </span>
                    )}
                </div>

                <span className="font-medium text-gray-900">
                    {question.question}
                </span>

                {question.ai_review?.rationale && (
                    <details className="text-xs text-gray-600">
                        <summary className="cursor-pointer select-none text-gray-500">
                            {t("admin.aiRationaleToggle")}
                        </summary>
                        <p className="mt-1 whitespace-pre-wrap">
                            {question.ai_review.rationale}
                        </p>
                    </details>
                )}

                <MarkdownContent content={question.answer} variant="full" />

                {hasConcepts && (
                    <div className="flex flex-wrap gap-1">
                        {question.concepts.map((concept) => (
                            <button
                                key={concept}
                                type="button"
                                onClick={() => onFilterConcept(concept)}
                                title={t("concepts.chipTitle", {
                                    concept,
                                })}
                                className={`cursor-pointer rounded-full px-2 py-0.5 text-xs transition-colors ${
                                    concept === activeConcept
                                        ? "bg-blue-600 text-white"
                                        : "bg-gray-100 text-gray-600 hover:bg-blue-50 hover:text-blue-700"
                                }`}
                            >
                                {concept}
                            </button>
                        ))}
                    </div>
                )}

                <ReferencedQuestions items={question.retrieved_questions} />

                <div
                    className="flex flex-wrap items-center gap-2 pt-1"
                    onClick={(e) => e.stopPropagation()}
                >
                    {question.status !== "APPROVED" && (
                        <Button
                            variant="secondary"
                            disabled={review?.state === "processing"}
                            onClick={() => onApprove()}
                        >
                            {t("common.approve")}
                        </Button>
                    )}

                    {question.status !== "REJECTED" && (
                        <Button
                            variant="secondary"
                            disabled={review?.state === "processing"}
                            onClick={() => onReject()}
                        >
                            {t("common.reject")}
                        </Button>
                    )}

                    <Link
                        href={`/admin/questions/${question.id}/reviews`}
                        className={buttonClassName("secondary")}
                    >
                        {t("common.history")}
                    </Link>

                    <Link
                        href={`/admin/questions/${question.id}/edit`}
                        className={buttonClassName("secondary")}
                    >
                        {t("common.edit")}
                    </Link>

                    {isAiReviewable(question) && (
                        <Button
                            variant="secondary"
                            disabled={aiBusy || aiReviewing}
                            onClick={() => onAiReview()}
                        >
                            {question.ai_review
                                ? t("admin.aiReviewCardAgain")
                                : t("admin.aiReviewCard")}
                        </Button>
                    )}

                    <Button
                        variant="secondary"
                        disabled={extraction === "processing"}
                        onClick={() => onExtract()}
                    >
                        {t("admin.extractConcepts")}
                    </Button>

                    <Button variant="danger" onClick={() => onDelete()}>
                        {t("common.delete")}
                    </Button>
                </div>
            </div>
        </Card>
    );
}
