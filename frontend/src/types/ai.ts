import { ContentLanguage, QuestionStatus } from "@/types/question";

export type AskAiResponse = {
    answer: string;
    language: ContentLanguage;
    // True when the answer came from an existing row instead of the LLM.
    cached: boolean;
    question_id: number | null;
    status: QuestionStatus | null;
};
