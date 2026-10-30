import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Question } from "@/types/question";

vi.mock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
    useParams: () => ({ id: "7" }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@/lib/api")>();
    return {
        ...actual,
        fetchQuestion: vi.fn(),
        reviewQuestion: vi.fn(),
        updateQuestion: vi.fn(),
        translateQuestions: vi.fn(),
    };
});

import * as api from "@/lib/api";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";
import EditQuestionPage from "@/app/admin/questions/[id]/edit/page";

const mocked = vi.mocked(api);

const QUESTION = {
    id: 7,
    question: "元の質問",
    answer: "元の回答",
    language: "ja",
    original_language: "ja",
    available_languages: ["ja", "en"],
    texts: {
        ja: { question: "元の質問", answer: "元の回答", provenance: "ORIGINAL" },
        en: {
            question: "Original question",
            answer: "Original answer",
            provenance: "MACHINE",
        },
    },
    status: "UNREVIEWED",
    source: "AI_GENERATED",
    concepts: [],
    retrieved_questions: [],
} as unknown as Question;

async function renderPage() {
    render(
        <LanguageProvider>
            <EditQuestionPage />
        </LanguageProvider>
    );
    await screen.findByDisplayValue("元の回答");
}

beforeEach(() => {
    mocked.fetchQuestion.mockReset().mockResolvedValue(QUESTION);
    mocked.reviewQuestion.mockReset().mockResolvedValue(QUESTION);
    mocked.updateQuestion.mockReset();
});

describe("AI suggestion", () => {
    const WITH_SUGGESTION = {
        ...QUESTION,
        ai_review: {
            verdict: "EDIT",
            confidence: 0.82,
            reasons: ["INCOMPLETE"],
            rationale: "説明が途中で終わっている。",
            suggested_answer: "AIの修正案",
            created_at: "2026-10-30T00:00:00Z",
        },
    } as unknown as Question;

    it("applies the suggested answer and sends it as an EDIT_APPROVE with the AI's reason", async () => {
        mocked.fetchQuestion.mockResolvedValue(WITH_SUGGESTION);
        const user = userEvent.setup();
        await renderPage();

        expect(screen.getByText("AIレビューの修正案")).toBeInTheDocument();
        expect(screen.getByText(/確信度 82%/)).toBeInTheDocument();

        await user.click(screen.getByRole("button", { name: "修正案を回答に反映" }));

        expect(screen.getByDisplayValue("AIの修正案")).toBeInTheDocument();
        expect(screen.getByText("AI提案を反映済み(未保存)")).toBeInTheDocument();
        // Nothing is persisted by applying alone.
        expect(mocked.updateQuestion).not.toHaveBeenCalled();
        expect(mocked.reviewQuestion).not.toHaveBeenCalled();

        await user.click(screen.getByRole("button", { name: "保存して承認" }));

        // The dialog opens with the AI's first reason preselected.
        const select = await screen.findByLabelText("理由");
        expect(select).toHaveValue("INCOMPLETE");
        await user.click(screen.getByRole("button", { name: "確定" }));

        await waitFor(() => expect(mocked.reviewQuestion).toHaveBeenCalled());
        expect(mocked.reviewQuestion).toHaveBeenCalledWith(7, {
            action: "EDIT_APPROVE",
            language: "ja",
            question: "元の質問",
            answer: "AIの修正案",
            reason: "INCOMPLETE",
            comment: undefined,
        });
    });

    it("shows no panel when there is no AI review", async () => {
        await renderPage();

        expect(screen.queryByText("AIレビューの修正案")).not.toBeInTheDocument();
    });
});

describe("Save and approve", () => {
    it("sends EDIT_APPROVE with the edited text so the diff is recorded", async () => {
        const user = userEvent.setup();
        await renderPage();

        const answer = screen.getByDisplayValue("元の回答");
        await user.clear(answer);
        await user.type(answer, "修正された回答");

        await user.click(
            screen.getByRole("button", { name: "保存して承認" })
        );

        // The edit must be labelled: pick a reason in the dialog first.
        await user.selectOptions(
            await screen.findByLabelText("理由"),
            "INCOMPLETE"
        );
        await user.click(screen.getByRole("button", { name: "確定" }));

        await waitFor(() => expect(mocked.reviewQuestion).toHaveBeenCalled());
        expect(mocked.reviewQuestion).toHaveBeenCalledTimes(1);
        expect(mocked.reviewQuestion).toHaveBeenCalledWith(7, {
            action: "EDIT_APPROVE",
            language: "ja",
            question: "元の質問",
            answer: "修正された回答",
            reason: "INCOMPLETE",
            comment: undefined,
        });
        // The edit travels inside the review, not as a separate update.
        expect(mocked.updateQuestion).not.toHaveBeenCalled();
    });

    it("sends a plain APPROVE when nothing changed", async () => {
        const user = userEvent.setup();
        await renderPage();

        await user.click(
            screen.getByRole("button", { name: "保存して承認" })
        );

        await waitFor(() => expect(mocked.reviewQuestion).toHaveBeenCalled());
        expect(mocked.reviewQuestion).toHaveBeenCalledWith(7, {
            action: "APPROVE",
        });
        expect(mocked.updateQuestion).not.toHaveBeenCalled();
    });

    it("reviews the machine translation before the original when both changed", async () => {
        const user = userEvent.setup();
        await renderPage();

        const ja = screen.getByDisplayValue("元の回答");
        await user.clear(ja);
        await user.type(ja, "修正された回答");

        const en = screen.getByDisplayValue("Original answer");
        await user.clear(en);
        await user.type(en, "Corrected answer");

        await user.click(
            screen.getByRole("button", { name: "保存して承認" })
        );
        await user.click(
            await screen.findByRole("button", { name: "確定" })
        );

        await waitFor(() =>
            expect(mocked.reviewQuestion).toHaveBeenCalledTimes(2)
        );
        expect(mocked.reviewQuestion.mock.calls[0][1].language).toBe("en");
        expect(mocked.reviewQuestion.mock.calls[1][1].language).toBe("ja");
        expect(mocked.reviewQuestion.mock.calls[0][1].reason).toBe(
            "PHYSICS_ERROR"
        );
    });
});
