import {
    BulkDeleteResponse,
    BulkReviewAction,
    BulkReviewResponse,
    ConceptExtractionBatchResponse,
    CreateQuestionRequest,
    FetchQuestionsParams,
    Question,
    QuestionImportResponse,
    QuestionListResponse,
    QuestionReview,
    QuestionSource,
    QuestionStatus,
    ReviewQuestionRequest,
    SearchQuestionsParams,
    SimilarQuestion,
    UpdateQuestionRequest,
} from "@/types/question";
import {
    AdminUser,
    AuthProviders,
    CreateUserRequest,
    LoginRequest,
    User,
} from "@/types/auth";
import {
    ContentLanguage,
    PrerequisitesResponse,
    TranslationBatchResponse,
} from "@/types/question";
import {
    AiReviewPendingCount,
    AiReviewRun,
    AiReviewRunScope,
} from "@/types/aiReviewRun";
import { AskAiResponse } from "@/types/ai";
import {
    AdminConcept,
    AdminConceptList,
    ConceptReviewFilter,
    ConceptSearchItem,
} from "@/types/concept";
import {
    AdminStatsResponse,
    MyQuestionsResponse,
    ReviewAgreementResponse,
    ReviewReason,
} from "@/types/question";

function getApiUrl(): string {
    const url = typeof window === "undefined"
    ? process.env.INTERNAL_API_URL
    : process.env.NEXT_PUBLIC_API_URL;

    if (!url) {
        throw new Error(
            "NEXT_PUBLIC_API_URL or INTERNAL_API_URL is not defined"
        );
    }

    return url;
}

function getQuestionsUrl(): string {
    return `${getApiUrl()}/api/v1/questions`;
}

function getAuthUrl(): string {
    return `${getApiUrl()}/api/v1/auth`;
}

function getUsersUrl(): string {
    return `${getApiUrl()}/api/v1/users`;
}

function getAiUrl(): string {
    return `${getApiUrl()}/api/v1/ai`;
}

export class ApiError extends Error {
    status: number;

    constructor(status: number, message: string) {
        super(message);
        this.name = "ApiError";
        this.status = status;
    }
}

async function apiFetch<T>(
    url: string,
    options?: RequestInit
): Promise<T> {
    const response = await fetch(url, {
        credentials: "include",
        ...options,
    });

    if (!response.ok) {
        throw new ApiError(
            response.status,
            `API request failed: ${options?.method ?? "GET"} ${url} (${response.status})`
        );
    }

    if (response.status === 204) {
        return undefined as T;
    }

    return response.json();
}

export async function fetchQuestions(
    params: FetchQuestionsParams = {}
): Promise<QuestionListResponse> {
    const searchParams = new URLSearchParams();

    if (params.page !== undefined) {
        searchParams.set("page", String(params.page));
    }
    if (params.size !== undefined) {
        searchParams.set("size", String(params.size));
    }
    if (params.keyword) {
        searchParams.set("keyword", params.keyword);
    }
    if (params.sort) {
        searchParams.set("sort", params.sort);
    }
    if (params.aiVerdict) {
        searchParams.set("ai_verdict", params.aiVerdict);
    }
    if (params.status) {
        searchParams.set("status", params.status);
    }
    if (params.searchQuestion !== undefined) {
        searchParams.set("search_question", String(params.searchQuestion));
    }
    if (params.searchAnswer !== undefined) {
        searchParams.set("search_answer", String(params.searchAnswer));
    }
    if (params.lang) {
        searchParams.set("lang", params.lang);
    }
    if (params.ids?.length) {
        searchParams.set("ids", params.ids.join(","));
    }
    if (params.concept) {
        searchParams.set("concept", params.concept);
    }
    if (params.conceptId !== undefined) {
        searchParams.set("concept_id", String(params.conceptId));
    }

    const query = searchParams.toString();

    return apiFetch<QuestionListResponse>(
        query ? `${getQuestionsUrl()}?${query}` : getQuestionsUrl()
    );
}

export async function searchQuestions(
    params: SearchQuestionsParams
): Promise<SimilarQuestion[]> {
    return apiFetch<SimilarQuestion[]>(`${getQuestionsUrl()}/search`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(params),
    });
}

export async function fetchQuestion(
    id: number,
    lang?: ContentLanguage
): Promise<Question> {
    const query = lang ? `?${new URLSearchParams({ lang })}` : "";
    return apiFetch<Question>(`${getQuestionsUrl()}/${id}${query}`);
}

export async function fetchQuestionByExactText(
    question: string,
    lang?: ContentLanguage
): Promise<Question> {
    const query = new URLSearchParams(
        lang ? { question, lang } : { question }
    ).toString();
    return apiFetch<Question>(`${getQuestionsUrl()}/exact-match?${query}`);
}

export async function deleteQuestion(id: number): Promise<void> {
    return apiFetch<void>(`${getQuestionsUrl()}/${id}`, {
        method: "DELETE",
    });
}

export async function createQuestion(
    data: CreateQuestionRequest
): Promise<Question> {
    return apiFetch<Question>(getQuestionsUrl(), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    });
}

export async function updateQuestion(
    data: UpdateQuestionRequest
): Promise<Question> {
    return apiFetch<Question>(`${getQuestionsUrl()}/${data.id}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    });
}

export async function login(data: LoginRequest): Promise<User> {
    return apiFetch<User>(`${getAuthUrl()}/login`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    });
}

export async function fetchAuthProviders(): Promise<AuthProviders> {
    return apiFetch<AuthProviders>(`${getAuthUrl()}/providers`);
}

// A plain navigation: the backend redirects the browser to Google.
export function getGoogleLoginUrl(): string {
    return `${getAuthUrl()}/google/login`;
}

export async function logout(): Promise<void> {
    return apiFetch<void>(`${getAuthUrl()}/logout`, {
        method: "POST",
    });
}

export async function fetchCurrentUser(): Promise<User> {
    return apiFetch<User>(`${getUsersUrl()}/me`);
}

export async function fetchReviewAgreement(): Promise<ReviewAgreementResponse> {
    return apiFetch<ReviewAgreementResponse>(
        `${getApiUrl()}/api/v1/admin/stats/review-agreement`
    );
}

export async function fetchAdminStats(
    days: number
): Promise<AdminStatsResponse> {
    return apiFetch<AdminStatsResponse>(
        `${getApiUrl()}/api/v1/admin/stats?days=${days}`
    );
}

export async function fetchMyQuestions(
    page: number,
    size: number,
    lang: ContentLanguage
): Promise<MyQuestionsResponse> {
    const params = new URLSearchParams({
        page: String(page),
        size: String(size),
        lang,
    });

    return apiFetch<MyQuestionsResponse>(
        `${getUsersUrl()}/me/questions?${params.toString()}`
    );
}

export async function fetchMyProfile(): Promise<AdminUser> {
    return apiFetch<AdminUser>(`${getUsersUrl()}/me/profile`);
}

export async function deleteMyAccount(): Promise<void> {
    return apiFetch<void>(`${getUsersUrl()}/me`, {
        method: "DELETE",
    });
}

export async function getUsers(): Promise<AdminUser[]> {
    return apiFetch<AdminUser[]>(getUsersUrl());
}

export async function createUser(data: CreateUserRequest): Promise<AdminUser> {
    return apiFetch<AdminUser>(getUsersUrl(), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    });
}

export async function deleteUser(id: number): Promise<void> {
    return apiFetch<void>(`${getUsersUrl()}/${id}`, {
        method: "DELETE",
    });
}

export async function fetchRelatedQuestions(
    id: number,
    limit = 5,
    lang?: ContentLanguage
): Promise<Question[]> {
    const langParam = lang ? `&lang=${lang}` : "";
    return apiFetch<Question[]>(
        `${getQuestionsUrl()}/${id}/related?limit=${limit}${langParam}`
    );
}

export async function fetchPrerequisites(
    id: number,
    lang?: ContentLanguage
): Promise<PrerequisitesResponse> {
    const langParam = lang ? `?lang=${lang}` : "";
    return apiFetch<PrerequisitesResponse>(
        `${getQuestionsUrl()}/${id}/prerequisites${langParam}`
    );
}

export async function translateQuestions(
    questionIds: number[]
): Promise<TranslationBatchResponse> {
    return apiFetch<TranslationBatchResponse>(`${getQuestionsUrl()}/translate`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ question_ids: questionIds }),
    });
}

export async function reviewQuestion(
    id: number,
    data: ReviewQuestionRequest
): Promise<Question> {
    return apiFetch<Question>(`${getQuestionsUrl()}/${id}/review`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    });
}

export async function fetchQuestionReviews(id: number): Promise<QuestionReview[]> {
    return apiFetch<QuestionReview[]>(`${getQuestionsUrl()}/${id}/reviews`);
}

export async function importQuestions(
    file: File,
    source: QuestionSource,
    status: QuestionStatus
): Promise<QuestionImportResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("source", source);
    formData.append("status", status);

    return apiFetch<QuestionImportResponse>(`${getQuestionsUrl()}/import`, {
        method: "POST",
        body: formData,
    });
}

export async function askAi(
    question: string,
    options: {
        language?: ContentLanguage;
        mode?: "RAG";
        retrievedQuestionIds?: number[];
    } = {}
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

export async function bulkDeleteQuestions(
    questionIds: number[]
): Promise<BulkDeleteResponse> {
    return apiFetch<BulkDeleteResponse>(`${getQuestionsUrl()}/bulk-delete`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ question_ids: questionIds }),
    });
}

export async function bulkReviewQuestions(
    questionIds: number[],
    action: BulkReviewAction,
    reason?: ReviewReason,
    comment?: string
): Promise<BulkReviewResponse> {
    return apiFetch<BulkReviewResponse>(`${getQuestionsUrl()}/bulk-review`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ question_ids: questionIds, action, reason, comment }),
    });
}

export async function extractConcepts(
    questionIds: number[]
): Promise<ConceptExtractionBatchResponse> {
    return apiFetch<ConceptExtractionBatchResponse>(
        `${getQuestionsUrl()}/concepts/extract`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ question_ids: questionIds }),
        }
    );
}

export async function fetchAiReviewPendingCount(): Promise<AiReviewPendingCount> {
    return apiFetch<AiReviewPendingCount>(
        `${getApiUrl()}/api/v1/admin/ai-review/pending-count`
    );
}

export async function fetchAiReviewRuns(limit = 10): Promise<AiReviewRun[]> {
    return apiFetch<AiReviewRun[]>(
        `${getApiUrl()}/api/v1/admin/ai-review/runs?limit=${limit}`
    );
}

export async function fetchAiReviewRun(id: number): Promise<AiReviewRun> {
    return apiFetch<AiReviewRun>(
        `${getApiUrl()}/api/v1/admin/ai-review/runs/${id}`
    );
}

export async function startAiReviewRun(params: {
    scope: AiReviewRunScope;
    questionIds?: number[];
}): Promise<AiReviewRun> {
    return apiFetch<AiReviewRun>(`${getApiUrl()}/api/v1/admin/ai-review/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            scope: params.scope,
            question_ids: params.questionIds,
        }),
    });
}

// --- concept senses ([55]) -----------------------------------------------------

function getConceptsUrl(): string {
    return `${getApiUrl()}/api/v1/concepts`;
}

function getAdminConceptsUrl(): string {
    return `${getApiUrl()}/api/v1/admin/concepts`;
}

function jsonInit(method: string, body: unknown): RequestInit {
    return {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    };
}

export async function searchConcepts(
    q: string,
    lang: ContentLanguage,
    limit = 20
): Promise<ConceptSearchItem[]> {
    const params = new URLSearchParams({ q, lang, limit: String(limit) });
    return apiFetch<ConceptSearchItem[]>(`${getConceptsUrl()}?${params}`);
}

export async function fetchAdminConcepts(params: {
    q?: string;
    filter?: ConceptReviewFilter;
    page?: number;
    size?: number;
}): Promise<AdminConceptList> {
    const search = new URLSearchParams({
        q: params.q ?? "",
        review_filter: params.filter ?? "all",
        page: String(params.page ?? 1),
        size: String(params.size ?? 30),
    });
    return apiFetch<AdminConceptList>(`${getAdminConceptsUrl()}?${search}`);
}

export async function fetchAdminConcept(
    id: number,
    lang: ContentLanguage
): Promise<AdminConcept> {
    return apiFetch<AdminConcept>(`${getAdminConceptsUrl()}/${id}?lang=${lang}`);
}

export async function updateConceptGloss(
    id: number,
    gloss: { gloss_ja: string | null; gloss_en: string | null },
    lang: ContentLanguage
): Promise<AdminConcept> {
    return apiFetch<AdminConcept>(
        `${getAdminConceptsUrl()}/${id}?lang=${lang}`,
        jsonInit("PATCH", gloss)
    );
}

export async function addConceptTerm(
    id: number,
    term: { language: ContentLanguage; term: string; is_preferred: boolean },
    lang: ContentLanguage
): Promise<AdminConcept> {
    return apiFetch<AdminConcept>(
        `${getAdminConceptsUrl()}/${id}/terms?lang=${lang}`,
        jsonInit("POST", term)
    );
}

export async function updateConceptTerm(
    termId: number,
    change: { term?: string; is_preferred?: boolean },
    lang: ContentLanguage
): Promise<AdminConcept> {
    return apiFetch<AdminConcept>(
        `${getAdminConceptsUrl()}/terms/${termId}?lang=${lang}`,
        jsonInit("PATCH", change)
    );
}

export async function deleteConceptTerm(termId: number): Promise<void> {
    return apiFetch<void>(`${getAdminConceptsUrl()}/terms/${termId}`, {
        method: "DELETE",
    });
}

export async function mergeConcept(
    id: number,
    intoId: number,
    lang: ContentLanguage
): Promise<AdminConcept> {
    return apiFetch<AdminConcept>(
        `${getAdminConceptsUrl()}/${id}/merge?lang=${lang}`,
        jsonInit("POST", { into_id: intoId })
    );
}

export async function splitConcept(
    id: number,
    body: {
        question_ids: number[];
        terms: { language: ContentLanguage; term: string }[];
        gloss_ja?: string;
        gloss_en?: string;
    },
    lang: ContentLanguage
): Promise<AdminConcept> {
    return apiFetch<AdminConcept>(
        `${getAdminConceptsUrl()}/${id}/split?lang=${lang}`,
        jsonInit("POST", body)
    );
}
