export type QuestionStatus = "UNREVIEWED" | "APPROVED" | "REJECTED";
export type QuestionSource = "MANUAL" | "AI_GENERATED";

export type Question = {
    id: number;
    question: string;
    answer: string;
    status: QuestionStatus;
    source: QuestionSource;
    language: string;
    concepts: string[];
};

export type QuestionListResponse = {
    items: Question[];
    total: number;
    page: number;
    size: number;
};

export type CreateQuestionRequest = {
    question: string;
    answer: string;
};

export type UpdateQuestionRequest = {
    id: number;
    question: string;
    answer: string;
};

export type SimilarQuestion = {
    id: number;
    question: string;
    answer: string;
    distance: number;
};

export type FetchQuestionsParams = {
    page?: number;
    size?: number;
    keyword?: string;
    status?: QuestionStatus;
};

export type SearchQuestionsParams = {
    query: string;
    limit?: number;
};

export type QuestionReviewAction = "APPROVE" | "EDIT_APPROVE" | "REJECT";

export type QuestionReview = {
    id: number;
    question_id: number;
    action: QuestionReviewAction;
    before_question: string | null;
    before_answer: string | null;
    after_question: string | null;
    after_answer: string | null;
    reviewer_id: number;
    comment: string | null;
    created_at: string;
};

export type ReviewQuestionRequest = {
    action: QuestionReviewAction;
    question?: string;
    answer?: string;
    comment?: string;
};

export type QuestionImportResponse = {
    created_count: number;
    questions: Question[];
};

export type BulkDeleteResponse = {
    deleted_count: number;
    not_found_ids: number[];
};

export type BulkReviewAction = "APPROVE" | "REJECT";

export type BulkReviewResponse = {
    questions: Question[];
    not_found_ids: number[];
};

export type ConceptExtractionResult = {
    question_id: number;
    success: boolean;
    concepts: string[];
};

export type ConceptExtractionBatchResponse = {
    results: ConceptExtractionResult[];
};
