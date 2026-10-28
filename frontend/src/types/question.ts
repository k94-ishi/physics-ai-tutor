export type QuestionStatus = "UNREVIEWED" | "APPROVED" | "REJECTED";
export type QuestionSource = "MANUAL" | "AI_GENERATED" | "RAG_RESULT";
export type ContentLanguage = "ja" | "en";
export type TextProvenance = "ORIGINAL" | "HUMAN" | "MACHINE";

export type LocalizedText = {
    question: string;
    answer: string;
    provenance: TextProvenance | null;
};

export type RetrievedQuestionRef = {
    id: number;
    question: string;
};

export type Question = {
    id: number;
    // Text resolved to the requested language (falls back to the original).
    question: string;
    answer: string;
    language: ContentLanguage;
    provenance: TextProvenance | null;
    original_language: ContentLanguage;
    available_languages: ContentLanguage[];
    texts: Partial<Record<ContentLanguage, LocalizedText>>;
    status: QuestionStatus;
    source: QuestionSource;
    concepts: string[];
    retrieved_questions: RetrievedQuestionRef[];
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
    language?: ContentLanguage;
};

export type UpdateQuestionRequest = {
    id: number;
    question_ja?: string;
    answer_ja?: string;
    question_en?: string;
    answer_en?: string;
};

export type SimilarQuestion = {
    id: number;
    question: string;
    answer: string;
    language: ContentLanguage;
    distance: number;
};

export type FetchQuestionsParams = {
    page?: number;
    size?: number;
    keyword?: string;
    status?: QuestionStatus;
    searchQuestion?: boolean;
    searchAnswer?: boolean;
    lang?: ContentLanguage;
};

export type SearchQuestionsParams = {
    query: string;
    limit?: number;
    language?: ContentLanguage;
};

export type QuestionReviewAction = "APPROVE" | "EDIT_APPROVE" | "REJECT";

export type QuestionReview = {
    id: number;
    question_id: number;
    action: QuestionReviewAction;
    language: ContentLanguage;
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
    language?: ContentLanguage;
    question?: string;
    answer?: string;
    comment?: string;
};

export type TranslationResult = {
    question_id: number;
    success: boolean;
    language: ContentLanguage | null;
};

export type TranslationBatchResponse = {
    results: TranslationResult[];
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

export type MyQuestionEntry = {
    question_id: number;
    question: string;
    answer: string | null;
    language: ContentLanguage;
    provenance: string | null;
    status: QuestionStatus;
    asked_at: string;
};

export type MyQuestionsResponse = {
    items: MyQuestionEntry[];
    total: number;
    page: number;
    size: number;
};
