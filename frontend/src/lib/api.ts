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
import { AdminUser, CreateUserRequest, LoginRequest, User } from "@/types/auth";
import { AskAiResponse } from "@/types/ai";

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

export async function fetchQuestion(id: number): Promise<Question> {
    return apiFetch<Question>(`${getQuestionsUrl()}/${id}`);
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

export async function logout(): Promise<void> {
    return apiFetch<void>(`${getAuthUrl()}/logout`, {
        method: "POST",
    });
}

export async function fetchCurrentUser(): Promise<User> {
    return apiFetch<User>(`${getUsersUrl()}/me`);
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
    limit = 5
): Promise<Question[]> {
    return apiFetch<Question[]>(
        `${getQuestionsUrl()}/${id}/related?limit=${limit}`
    );
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

export async function askAi(question: string): Promise<AskAiResponse> {
    return apiFetch<AskAiResponse>(`${getAiUrl()}/ask`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ question }),
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
    comment?: string
): Promise<BulkReviewResponse> {
    return apiFetch<BulkReviewResponse>(`${getQuestionsUrl()}/bulk-review`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ question_ids: questionIds, action, comment }),
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
