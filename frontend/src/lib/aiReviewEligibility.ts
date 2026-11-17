import { Question } from "@/types/question";

/** Only unreviewed AI answers can be AI-reviewed ([28]). */
export function isAiReviewable(question: Question): boolean {
    return (
        question.status === "UNREVIEWED" &&
        (question.source === "AI_GENERATED" || question.source === "RAG_RESULT")
    );
}

/** Split a selection into reviewable and skipped rows, for the confirm dialog. */
export function splitAiReviewSelection(
    questions: Question[],
    selectedIds: Set<number>
): { eligibleIds: number[]; skippedCount: number } {
    const eligibleIds: number[] = [];
    let skippedCount = 0;

    for (const question of questions) {
        if (!selectedIds.has(question.id)) {
            continue;
        }
        if (isAiReviewable(question)) {
            eligibleIds.push(question.id);
        } else {
            skippedCount += 1;
        }
    }

    return { eligibleIds, skippedCount };
}
