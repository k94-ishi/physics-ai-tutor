"use client";

import { ReactNode } from "react";
import Card from "@/components/ui/Card";
import ConceptChips from "@/components/ui/ConceptChips";
import MarkdownContent from "@/components/ui/MarkdownContent";
import { Question } from "@/types/question";

/** Cards show a few tags; the rest open with "more". */
export const CARD_TAGS_VISIBLE = 5;

const TONE_CLASSES = {
    // Related questions and the home list.
    blue: "hover:border-blue-300 hover:bg-blue-50/50",
    // "Read these first": the prerequisite direction ([38]).
    emerald: "hover:border-emerald-300 hover:bg-emerald-50/50",
} as const;

type QuestionCardProps = {
    question: Pick<Question, "id" | "question" | "answer" | "concepts">;
    onOpen: () => void;
    tone?: keyof typeof TONE_CLASSES;
    /** Extra content under the tags, e.g. referenced questions. */
    children?: ReactNode;
};

/**
 * A question with an answer preview and its tags ([63]).
 *
 * The text is a button that opens the preview; the tags are links, so
 * they sit beside the button rather than inside it.
 */
export default function QuestionCard({
    question,
    onOpen,
    tone = "blue",
    children,
}: QuestionCardProps) {
    return (
        <Card className={`flex flex-col gap-2 transition-colors ${TONE_CLASSES[tone]}`}>
            <button
                type="button"
                onClick={onOpen}
                className="flex w-full cursor-pointer flex-col gap-1 text-left"
            >
                <span className="font-medium text-gray-900">{question.question}</span>

                <MarkdownContent content={question.answer} variant="preview" />
            </button>

            <ConceptChips concepts={question.concepts} visible={CARD_TAGS_VISIBLE} />

            {children}
        </Card>
    );
}
