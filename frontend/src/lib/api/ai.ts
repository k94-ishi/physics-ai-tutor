// Asking the AI ([64]); streamed answers ([71]).

import { AskAiResponse } from "@/types/ai";
import { ContentLanguage } from "@/types/question";
import { ApiError, apiFetch, getAiUrl } from "@/lib/api/client";

type AskOptions = {
    language?: ContentLanguage;
    mode?: "RAG";
    retrievedQuestionIds?: number[];
};

function askBody(question: string, options: AskOptions): string {
    return JSON.stringify({
        question,
        language: options.language,
        mode: options.mode,
        retrieved_question_ids: options.retrievedQuestionIds,
    });
}

export async function askAi(
    question: string,
    options: AskOptions = {},
): Promise<AskAiResponse> {
    return apiFetch<AskAiResponse>(`${getAiUrl()}/ask`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: askBody(question, options),
    });
}

export type AskStreamHandlers = {
    // Called with each piece of the answer as it arrives.
    onDelta: (text: string) => void;
};

/**
 * Ask over SSE so the answer can be rendered while it generates ([71]).
 *
 * Resolves with the same payload `askAi` returns, assembled from the
 * final `done` event. `EventSource` cannot POST, so this reads the body
 * stream directly. Callers should fall back to `askAi` on failure.
 */
export async function askAiStream(
    question: string,
    options: AskOptions = {},
    handlers: AskStreamHandlers,
): Promise<AskAiResponse> {
    const response = await fetch(`${getAiUrl()}/ask/stream`, {
        credentials: "include",
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: askBody(question, options),
    });

    if (!response.ok) {
        throw new ApiError(
            response.status,
            `API request failed: POST ${getAiUrl()}/ask/stream (${response.status})`,
        );
    }

    if (!response.body) {
        throw new Error("Streaming is not supported by this browser");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let done: AskAiResponse | null = null;
    let failure: string | null = null;

    const handleFrame = (frame: string) => {
        let name = "";
        const dataLines: string[] = [];

        for (const line of frame.split("\n")) {
            if (line.startsWith("event: ")) {
                name = line.slice("event: ".length);
            } else if (line.startsWith("data: ")) {
                dataLines.push(line.slice("data: ".length));
            }
        }

        if (dataLines.length === 0) {
            return;
        }

        const payload = JSON.parse(dataLines.join("\n"));

        if (name === "delta") {
            handlers.onDelta(payload.text ?? "");
        } else if (name === "done") {
            done = payload as AskAiResponse;
        } else if (name === "error") {
            failure = payload.detail ?? "Generation failed";
        }
    };

    try {
        for (;;) {
            const { value, done: finished } = await reader.read();

            if (finished) {
                break;
            }

            buffer += decoder.decode(value, { stream: true });

            // Frames are separated by a blank line; keep any partial tail.
            const frames = buffer.split("\n\n");
            buffer = frames.pop() ?? "";

            for (const frame of frames) {
                if (frame.trim()) {
                    handleFrame(frame);
                }
            }
        }

        if (buffer.trim()) {
            handleFrame(buffer);
        }
    } finally {
        reader.releaseLock();
    }

    if (failure !== null) {
        throw new Error(failure);
    }

    if (done === null) {
        throw new Error("Stream ended before the answer was complete");
    }

    return done;
}
