import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
    ApiError,
    askAi,
    bulkReviewQuestions,
    deleteQuestion,
    fetchQuestions,
    importQuestions,
    login,
    searchQuestions,
} from "@/lib/api";

function jsonResponse(body: unknown, status = 200): Response {
    return new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
    });
}

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
    vi.unstubAllGlobals();
});

function lastRequest(): { url: string; init: RequestInit } {
    const [url, init] = fetchMock.mock.calls.at(-1) as [string, RequestInit];
    return { url, init };
}

describe("apiFetch behaviour", () => {
    it("sends cookies with every request", async () => {
        fetchMock.mockResolvedValue(jsonResponse({ items: [], total: 0, page: 1, size: 30 }));

        await fetchQuestions();

        expect(lastRequest().init.credentials).toBe("include");
    });

    it("throws ApiError with the HTTP status on failure", async () => {
        fetchMock.mockResolvedValue(jsonResponse({ detail: "nope" }, 403));

        await expect(deleteQuestion(1)).rejects.toMatchObject({
            name: "ApiError",
            status: 403,
        });
    });

    it("returns undefined for 204 responses", async () => {
        fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

        await expect(deleteQuestion(1)).resolves.toBeUndefined();
        expect(lastRequest().init.method).toBe("DELETE");
    });

    it("ApiError is an Error instance", () => {
        const error = new ApiError(500, "x");
        expect(error).toBeInstanceOf(Error);
        expect(error.message).toBe("x");
    });
});

describe("fetchQuestions", () => {
    it("omits unset params and serialises the rest", async () => {
        fetchMock.mockResolvedValue(jsonResponse({ items: [], total: 0, page: 2, size: 60 }));

        await fetchQuestions({
            page: 2,
            size: 60,
            keyword: "速度 加速度",
            searchAnswer: false,
        });

        const url = new URL(lastRequest().url);
        expect(url.pathname).toBe("/api/v1/questions");
        expect(url.searchParams.get("page")).toBe("2");
        expect(url.searchParams.get("size")).toBe("60");
        expect(url.searchParams.get("keyword")).toBe("速度 加速度");
        expect(url.searchParams.get("search_answer")).toBe("false");
        expect(url.searchParams.has("status")).toBe(false);
        expect(url.searchParams.has("search_question")).toBe(false);
    });

    it("builds a bare URL when no params are given", async () => {
        fetchMock.mockResolvedValue(jsonResponse({ items: [], total: 0, page: 1, size: 30 }));

        await fetchQuestions();

        expect(lastRequest().url).toBe("http://api.test/api/v1/questions");
    });
});

describe("JSON endpoints", () => {
    it("searchQuestions posts the query as JSON", async () => {
        fetchMock.mockResolvedValue(jsonResponse([]));

        await searchQuestions({ query: "速度", limit: 3 });

        const { url, init } = lastRequest();
        expect(url).toBe("http://api.test/api/v1/questions/search");
        expect(init.method).toBe("POST");
        expect(JSON.parse(init.body as string)).toEqual({ query: "速度", limit: 3 });
    });

    it("login posts credentials and returns the user", async () => {
        fetchMock.mockResolvedValue(jsonResponse({ id: 1, role: "admin" }));

        const user = await login({ email: "a@example.com", password: "secret12" });

        expect(user).toEqual({ id: 1, role: "admin" });
        expect(lastRequest().url).toBe("http://api.test/api/v1/auth/login");
    });

    it("bulkReviewQuestions sends ids, action and comment", async () => {
        fetchMock.mockResolvedValue(jsonResponse({ updated_count: 2, not_found_ids: [] }));

        await bulkReviewQuestions([1, 2], "APPROVE", "ok");

        expect(JSON.parse(lastRequest().init.body as string)).toEqual({
            question_ids: [1, 2],
            action: "APPROVE",
            comment: "ok",
        });
    });

    it("askAi sends the question and optional RAG fields", async () => {
        fetchMock.mockResolvedValue(jsonResponse({ answer: "回答" }));

        const result = await askAi("速度ってなに？", "RAG", [4, 7]);

        expect(result.answer).toBe("回答");
        const body = JSON.parse(lastRequest().init.body as string);
        expect(body.question).toBe("速度ってなに？");
        expect(body.mode).toBe("RAG");
        expect(body.retrieved_question_ids).toEqual([4, 7]);
    });
});

describe("importQuestions", () => {
    it("uploads multipart form data with status and source", async () => {
        fetchMock.mockResolvedValue(jsonResponse({ created_count: 1, questions: [] }));
        const file = new File(['{"question":"q","answer":"a"}'], "q.jsonl");

        await importQuestions(file, "MANUAL", "APPROVED");

        const body = lastRequest().init.body as FormData;
        expect(body).toBeInstanceOf(FormData);
        expect(body.get("source")).toBe("MANUAL");
        expect(body.get("status")).toBe("APPROVED");
        expect(body.get("file")).toBeInstanceOf(File);
    });
});
