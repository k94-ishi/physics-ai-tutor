import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
        question_physics_level: null,
        question_math_level: null,
        answer_physics_level: null,
        answer_math_level: null,
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
        expect(mocked.fetchRelatedQuestions).toHaveBeenCalledWith(1, 20, "ja");
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

describe("concept chips", () => {
    it("shows the answer's concepts as links to the shared-concept list", async () => {
        mocked.fetchQuestion.mockResolvedValue(
            makeQuestion({ concepts: ["微分方程式", "終端速度"] })
        );
        mocked.fetchRelatedQuestions.mockResolvedValue([]);
        renderDetail();

        const chip = await screen.findByRole("link", { name: "微分方程式" });
        expect(chip).toHaveAttribute(
            "href",
            "/?concept=%E5%BE%AE%E5%88%86%E6%96%B9%E7%A8%8B%E5%BC%8F"
        );
    });

    it("shows no concept section when the question has none", async () => {
        mocked.fetchQuestion.mockResolvedValue(makeQuestion({ concepts: [] }));
        mocked.fetchRelatedQuestions.mockResolvedValue([]);
        renderDetail();

        await screen.findByText("速度ってなに？");
        expect(
            screen.queryByText("この回答に出てくる概念")
        ).not.toBeInTheDocument();
    });
});

describe("related questions", () => {
    function makeRelated(count: number) {
        return Array.from({ length: count }, (_, i) =>
            makeQuestion({
                id: 100 + i,
                question: `関連質問${String(i).padStart(2, "0")}`,
                answer: `関連回答${i}`,
            })
        );
    }

    it("asks for the API maximum and shows ten before expanding", async () => {
        mocked.fetchQuestion.mockResolvedValue(makeQuestion({}));
        mocked.fetchRelatedQuestions.mockResolvedValue(makeRelated(14));
        const user = userEvent.setup();
        renderDetail();

        await screen.findByText("関連質問00");
        expect(mocked.fetchRelatedQuestions).toHaveBeenCalledWith(1, 20, "ja");
        expect(screen.queryByText("関連質問10")).not.toBeInTheDocument();

        // Expanding costs no extra request: the rest is already loaded.
        await user.click(
            screen.getByRole("button", { name: "関連する質問をもっと見る" })
        );
        expect(screen.getByText("関連質問13")).toBeInTheDocument();
        expect(mocked.fetchRelatedQuestions).toHaveBeenCalledTimes(1);
    });

    it("previews a related question without leaving the page", async () => {
        mocked.fetchQuestion.mockResolvedValue(makeQuestion({}));
        mocked.fetchRelatedQuestions.mockResolvedValue(makeRelated(1));
        const user = userEvent.setup();
        renderDetail();

        await user.click(await screen.findByRole("button", { name: /関連質問00/ }));

        const dialog = screen.getByRole("dialog");
        expect(dialog).toHaveTextContent("関連質問00");
        // The original question is still mounted behind the modal.
        expect(screen.getByText("速度ってなに？")).toBeInTheDocument();
        expect(
            screen.getByRole("link", { name: "この質問のページを開く" })
        ).toHaveAttribute("href", "/questions/100");

        await user.click(screen.getByRole("button", { name: "閉じる" }));
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("offers no expansion when ten or fewer are related", async () => {
        mocked.fetchQuestion.mockResolvedValue(makeQuestion({}));
        mocked.fetchRelatedQuestions.mockResolvedValue(makeRelated(3));
        renderDetail();

        await screen.findByText("関連質問00");
        expect(
            screen.queryByRole("button", { name: "関連する質問をもっと見る" })
        ).not.toBeInTheDocument();
    });
});
