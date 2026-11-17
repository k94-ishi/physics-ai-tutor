// Shared HTTP plumbing: base URLs, fetch wrapper, errors ([64]).

export function getApiUrl(): string {
    const url =
        typeof window === "undefined"
            ? process.env.INTERNAL_API_URL
            : process.env.NEXT_PUBLIC_API_URL;

    if (!url) {
        throw new Error(
            "NEXT_PUBLIC_API_URL or INTERNAL_API_URL is not defined",
        );
    }

    return url;
}

export function getQuestionsUrl(): string {
    return `${getApiUrl()}/api/v1/questions`;
}

export function getAuthUrl(): string {
    return `${getApiUrl()}/api/v1/auth`;
}

export function getUsersUrl(): string {
    return `${getApiUrl()}/api/v1/users`;
}

export function getAiUrl(): string {
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

export async function apiFetch<T>(
    url: string,
    options?: RequestInit,
): Promise<T> {
    const response = await fetch(url, {
        credentials: "include",
        ...options,
    });

    if (!response.ok) {
        throw new ApiError(
            response.status,
            `API request failed: ${options?.method ?? "GET"} ${url} (${response.status})`,
        );
    }

    if (response.status === 204) {
        return undefined as T;
    }

    return response.json();
}

export function getConceptsUrl(): string {
    return `${getApiUrl()}/api/v1/concepts`;
}

export function getAdminConceptsUrl(): string {
    return `${getApiUrl()}/api/v1/admin/concepts`;
}

export function jsonInit(method: string, body: unknown): RequestInit {
    return {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    };
}
