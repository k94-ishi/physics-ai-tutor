import { describe, expect, it } from "vitest";
import {
    isAiReviewable,
    splitAiReviewSelection,
} from "@/lib/aiReviewEligibility";
import { Question } from "@/types/question";

function makeQuestion(overrides: Partial<Question>): Question {
    return {
        id: 1,
        status: "UNREVIEWED",
        source: "AI_GENERATED",
        ...overrides,
    } as Question;
}

const QUESTIONS = [
    { id: 1, status: "UNREVIEWED", source: "AI_GENERATED" },
    { id: 2, status: "UNREVIEWED", source: "RAG_RESULT" },
    { id: 3, status: "UNREVIEWED", source: "MANUAL" },
    { id: 4, status: "APPROVED", source: "AI_GENERATED" },
] as Question[];

describe("splitAiReviewSelection", () => {
    it("reviews the unreviewed AI rows and reports the rest as skipped", () => {
        // The [28] acceptance case: 2 AI questions and 1 manual one.
        const result = splitAiReviewSelection(QUESTIONS, new Set([1, 2, 3]));

        expect(result.eligibleIds).toEqual([1, 2]);
        expect(result.skippedCount).toBe(1);
    });

    it("skips already-reviewed AI answers", () => {
        const result = splitAiReviewSelection(QUESTIONS, new Set([1, 4]));

        expect(result.eligibleIds).toEqual([1]);
        expect(result.skippedCount).toBe(1);
    });

    it("ignores rows that are not selected", () => {
        const result = splitAiReviewSelection(QUESTIONS, new Set());

        expect(result.eligibleIds).toEqual([]);
        expect(result.skippedCount).toBe(0);
    });
});

describe("isAiReviewable", () => {
    it("accepts only unreviewed AI-generated or RAG answers", () => {
        expect(isAiReviewable(QUESTIONS[0])).toBe(true);
        expect(isAiReviewable(QUESTIONS[1])).toBe(true);
        expect(isAiReviewable(QUESTIONS[2])).toBe(false);
        expect(isAiReviewable(QUESTIONS[3])).toBe(false);
        expect(
            makeQuestion({}) !== null && isAiReviewable(makeQuestion({}))
        ).toBe(true);
    });
});
