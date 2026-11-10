// Asking the AI ([64]).

import { AskAiResponse } from "@/types/ai";
import { ContentLanguage } from "@/types/question";
import { apiFetch, getAiUrl } from "@/lib/api/client";

export async function askAi(
    question: string,
    options: {
        language?: ContentLanguage;
        mode?: "RAG";
        retrievedQuestionIds?: number[];
    } = {},
): Promise<AskAiResponse> {
    return apiFetch<AskAiResponse>(`${getAiUrl()}/ask`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            question,
            language: options.language,
            mode: options.mode,
            retrieved_question_ids: options.retrievedQuestionIds,
        }),
    });
}
