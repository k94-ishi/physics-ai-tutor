import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Question } from "@/types/question";

vi.mock("@/lib/api", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@/lib/api")>();
    return {
        ...actual,
        fetchQuestion: vi.fn(),
        fetchRelatedQuestions: vi.fn(),
    };
});

import * as api from "@/lib/api";
import QuestionDetail from "@/components/QuestionDetail";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";

const mocked = vi.mocked(api);

function makeQuestion(overrides: Partial<Question> = {}): Question {
    return {
        id: 1,
        question: "速度ってなに？",
        answer: "向きを含む速さです。",
        language: "ja",
        provenance: "ORIGINAL",
        original_language: "ja",
        available_languages: ["ja", "en"],
        texts: {},
        status: "APPROVED",
        source: "MANUAL",
        concepts: [],
        retrieved_questions: [],
        ...overrides,
    };
}

function renderDetail() {
    render(
        <LanguageProvider>
            <QuestionDetail id={1} />
        </LanguageProvider>
    );
}

beforeEach(() => {
    mocked.fetchQuestion.mockReset();
    mocked.fetchRelatedQuestions.mockReset();
    mocked.fetchRelatedQuestions.mockResolvedValue([]);
});

describe("QuestionDetail", () => {
    it("fetches in the active language and renders the text", async () => {
        mocked.fetchQuestion.mockResolvedValue(makeQuestion());

        renderDetail();

        await waitFor(() =>
            expect(screen.getByText("速度ってなに？")).toBeInTheDocument()
        );
        expect(mocked.fetchQuestion).toHaveBeenCalledWith(1, "ja");
        expect(mocked.fetchRelatedQuestions).toHaveBeenCalledWith(1, 5, "ja");
        expect(screen.queryByText("自動翻訳")).not.toBeInTheDocument();
        expect(screen.queryByText("管理者未チェック")).not.toBeInTheDocument();
    });

    it("labels approved machine translations as translated from reviewed content", async () => {
        mocked.fetchQuestion.mockResolvedValue(
            makeQuestion({ language: "en", provenance: "MACHINE" })
        );

        renderDetail();

        await waitFor(() =>
            expect(
                screen.getByText("レビュー済みの内容を自動翻訳")
            ).toBeInTheDocument()
        );
    });

    it("shows both badges for an unreviewed machine translation", async () => {
        mocked.fetchQuestion.mockResolvedValue(
            makeQuestion({ status: "UNREVIEWED", provenance: "MACHINE" })
        );

        renderDetail();

        await waitFor(() =>
            expect(screen.getByText("管理者未チェック")).toBeInTheDocument()
        );
        expect(screen.getByText("自動翻訳")).toBeInTheDocument();
    });

    it("shows an error state with retry when loading fails", async () => {
        mocked.fetchQuestion.mockRejectedValue(new api.ApiError(500, "boom"));
        vi.spyOn(console, "error").mockImplementation(() => {});

        renderDetail();

        await waitFor(() =>
            expect(screen.getByRole("alert")).toBeInTheDocument()
        );
    });
});
