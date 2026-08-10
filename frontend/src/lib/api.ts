import {
    CreateQuestionRequest,
    Question,
    QuestionListResponse,
    UpdateQuestionRequest,
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
    const response = await fetch(url, options);

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

export async function fetchQuestions(): Promise<QuestionListResponse> {
    return apiFetch<QuestionListResponse>(getQuestionsUrl());
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
