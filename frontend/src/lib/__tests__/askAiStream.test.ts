// Streamed answers over SSE ([71]).

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, askAiStream } from "@/lib/api";

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
    vi.unstubAllGlobals();
});

/** An SSE response whose body arrives in the given raw pieces. */
function sseResponse(pieces: string[], status = 200): Response {
    const encoder = new TextEncoder();
    const body = new ReadableStream<Uint8Array>({
        start(controller) {
            for (const piece of pieces) {
                controller.enqueue(encoder.encode(piece));
            }
            controller.close();
        },
    });

    return new Response(body, {
        status,
        headers: { "Content-Type": "text/event-stream" },
    });
}

function frame(name: string, payload: unknown): string {
    return `event: ${name}\ndata: ${JSON.stringify(payload)}\n\n`;
}

const DONE = {
    answer: "加速度とは速度の変化率です。",
    language: "ja",
    cached: false,
    question_id: 7,
    status: "UNREVIEWED",
};

describe("askAiStream", () => {
    it("reports each delta and resolves with the done payload", async () => {
        fetchMock.mockResolvedValue(
            sseResponse([
                frame("delta", { text: "加速度とは" }),
                frame("delta", { text: "速度の変化率" }),
                frame("delta", { text: "です。" }),
                frame("done", DONE),
            ]),
        );

        const deltas: string[] = [];
        const result = await askAiStream(
            "加速度とは何ですか",
            {},
            { onDelta: (text) => deltas.push(text) },
        );

        expect(deltas).toEqual(["加速度とは", "速度の変化率", "です。"]);
        expect(result).toEqual(DONE);
    });

    it("posts the question, language and mode", async () => {
        fetchMock.mockResolvedValue(sseResponse([frame("done", DONE)]));

        await askAiStream(
            "運動量とは",
            { language: "en", mode: "RAG", retrievedQuestionIds: [1, 2] },
            { onDelta: () => {} },
        );

        const [url, init] = fetchMock.mock.calls[0];
        expect(String(url)).toContain("/api/v1/ai/ask/stream");
        expect(init?.method).toBe("POST");
        expect(JSON.parse(String(init?.body))).toEqual({
            question: "運動量とは",
            language: "en",
            mode: "RAG",
            retrieved_question_ids: [1, 2],
        });
    });

    it("reassembles frames split across chunk boundaries", async () => {
        // The network does not respect frame boundaries.
        const whole =
            frame("delta", { text: "前半" }) +
            frame("delta", { text: "後半" }) +
            frame("done", DONE);
        const split = [whole.slice(0, 17), whole.slice(17, 40), whole.slice(40)];

        fetchMock.mockResolvedValue(sseResponse(split));

        const deltas: string[] = [];
        const result = await askAiStream(
            "分割された質問",
            {},
            { onDelta: (text) => deltas.push(text) },
        );

        expect(deltas.join("")).toBe("前半後半");
        expect(result.question_id).toBe(7);
    });

    it("keeps newlines inside an answer intact", async () => {
        const answer = "一行目\n\n二行目";
        fetchMock.mockResolvedValue(
            sseResponse([
                frame("delta", { text: answer }),
                frame("done", { ...DONE, answer }),
            ]),
        );

        const deltas: string[] = [];
        const result = await askAiStream(
            "改行を含む回答の質問",
            {},
            { onDelta: (text) => deltas.push(text) },
        );

        expect(deltas).toEqual([answer]);
        expect(result.answer).toBe(answer);
    });

    it("throws on an error event so the caller can fall back", async () => {
        fetchMock.mockResolvedValue(
            sseResponse([
                frame("delta", { text: "途中まで" }),
                frame("error", { detail: "DeepSeek generation failed." }),
            ]),
        );

        await expect(
            askAiStream("失敗する質問", {}, { onDelta: () => {} }),
        ).rejects.toThrow("DeepSeek generation failed.");
    });

    it("throws ApiError on a non-2xx response", async () => {
        fetchMock.mockResolvedValue(sseResponse([], 429));

        await expect(
            askAiStream("制限された質問", {}, { onDelta: () => {} }),
        ).rejects.toBeInstanceOf(ApiError);
    });

    it("throws when the stream ends without a done event", async () => {
        fetchMock.mockResolvedValue(
            sseResponse([frame("delta", { text: "途中で切れた" })]),
        );

        await expect(
            askAiStream("切断される質問", {}, { onDelta: () => {} }),
        ).rejects.toThrow(/complete/);
    });
});
