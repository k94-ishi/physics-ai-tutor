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
import { ContentLanguage, TranslationBatchResponse } from "@/types/question";
import { AskAiResponse } from "@/types/ai";
import {
    AdminStatsResponse,
    MyQuestionsResponse,
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
