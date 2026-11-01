import { Question } from "@/types/question";

/** AIレビューの対象になれるのは未レビューのAI生成回答だけ([28])。 */
export function isAiReviewable(question: Question): boolean {
    return (
        question.status === "UNREVIEWED" &&
        (question.source === "AI_GENERATED" || question.source === "RAG_RESULT")
    );
}

/**
 * 選択された行をAIレビュー対象と対象外に分ける。確認ダイアログが
 * 「2件を判定、1件は対象外」と事前に言えるようにするための分割。
 */
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
