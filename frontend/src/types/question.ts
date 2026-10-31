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
    generation?: GenerationMeta | null;
    ai_review?: AiReviewSummary | null;
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

export type QuestionSort = "oldest" | "ai_confidence" | "asked_count";
export type AiVerdictFilter = "APPROVE" | "EDIT" | "REJECT" | "NONE";

export type FetchQuestionsParams = {
    page?: number;
    size?: number;
    keyword?: string;
    status?: QuestionStatus;
    searchQuestion?: boolean;
    searchAnswer?: boolean;
    lang?: ContentLanguage;
    sort?: QuestionSort;
    aiVerdict?: AiVerdictFilter;
};

export type SearchQuestionsParams = {
    query: string;
    limit?: number;
    language?: ContentLanguage;
};

export type QuestionReviewAction = "APPROVE" | "EDIT_APPROVE" | "REJECT";

export const REVIEW_REASONS = [
    "PHYSICS_ERROR",
    "MATH_ERROR",
    "INCOMPLETE",
    "OFF_TOPIC",
    "TOO_ADVANCED",
    "UNCLEAR",
    "FORMATTING",
    "LANGUAGE",
    "DUPLICATE",
    "OTHER",
] as const;

export type ReviewReason = (typeof REVIEW_REASONS)[number];

export type AiVerdict = "APPROVE" | "EDIT" | "REJECT";

// Latest AI pre-review verdict; present only in admin responses.
export type AiReviewSummary = {
    verdict: AiVerdict | null;
    confidence: number | null;
    reasons: ReviewReason[];
    rationale: string | null;
    suggested_answer: string | null;
    created_at: string;
};

export type QuestionReview = {
    id: number;
    question_id: number;
    action: QuestionReviewAction;
    reason: ReviewReason | null;
    reviewer_kind: "human" | "ai" | "policy";
    policy_name: string | null;
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
    reason?: ReviewReason;
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

// Present only in admin responses; null fields for manual rows.
export type GenerationMeta = {
    model: string | null;
    prompt_version: string | null;
    mode: "DIRECT" | "RAG" | null;
    prompt_tokens: number | null;
    completion_tokens: number | null;
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

export type DailyUsage = {
    day: string;
    generations: number;
    asks: number;
    cache_hits: number;
    distinct_users: number;
};

export type AdminStatsResponse = {
    days: number;
    daily: DailyUsage[];
    unreviewed_count: number;
    unreviewed_median_age_days: number | null;
    anonymous_ip_buckets_24h: number;
};

export type CalibrationBucket = {
    low: number;
    high: number;
    n: number;
    agreement_rate: number | null;
};

export type AgreementMetrics = {
    n: number;
    sufficient: boolean;
    exact_agreement_rate: number | null;
    publish_agreement_rate: number | null;
    reject_precision: number | null;
    reject_recall: number | null;
    reason_jaccard_mean: number | null;
    confusion_matrix: Record<string, Record<string, number>>;
    calibration: CalibrationBucket[];
};

export type ReviewAgreementResponse = {
    since: string | null;
    overall: AgreementMetrics;
    by_answer_prompt_version: Record<string, AgreementMetrics>;
    by_reviewer_prompt_version: Record<string, AgreementMetrics>;
    by_month: Record<string, AgreementMetrics>;
};
