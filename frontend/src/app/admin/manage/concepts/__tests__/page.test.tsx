import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@/lib/api")>();
    return {
        ...actual,
        fetchAdminConcepts: vi.fn(),
        fetchAdminConcept: vi.fn(),
        updateConceptTerm: vi.fn(),
        splitConcept: vi.fn(),
    };
});

import * as api from "@/lib/api";
import AdminConceptsPage from "@/app/admin/manage/concepts/page";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";
import { AdminConcept } from "@/types/concept";

const mocked = vi.mocked(api);

const velocity: AdminConcept = {
    id: 7,
    gloss_ja: null,
    gloss_en: null,
    question_count: 2,
    shares_word_with: [9],
    questions: [
        { id: 101, question: "速度とは？", status: "APPROVED" },
        { id: 102, question: "速さとは？", status: "APPROVED" },
    ],
    terms: [
        { id: 1, language: "ja", term: "速度", is_preferred: true, source: "EXTRACTED" },
        { id: 2, language: "en", term: "velocity", is_preferred: true, source: "EXTRACTED" },
        { id: 3, language: "en", term: "speed", is_preferred: false, source: "MACHINE" },
    ],
};

function renderPage() {
    render(
        <LanguageProvider>
            <AdminConceptsPage />
        </LanguageProvider>
    );
}

beforeEach(() => {
    vi.clearAllMocks();
    mocked.fetchAdminConcepts.mockResolvedValue({
        items: [velocity],
        total: 1,
        page: 1,
        size: 30,
    });
    mocked.fetchAdminConcept.mockResolvedValue(velocity);
});

describe("AdminConceptsPage", () => {
    it("shows every word of a sense, machine words and shared-word partners", async () => {
        renderPage();

        expect(await screen.findByText("velocity / speed")).toBeInTheDocument();
        expect(screen.getByText("語を共有: #9")).toBeInTheDocument();
        expect(screen.getByText("機械翻訳")).toBeInTheDocument();
    });

    it("makes an alias the label", async () => {
        mocked.updateConceptTerm.mockResolvedValue(velocity);
        renderPage();

        await userEvent.click(await screen.findByText("velocity / speed"));
        await userEvent.click(await screen.findByRole("button", { name: "表示名にする" }));

        expect(mocked.updateConceptTerm).toHaveBeenCalledWith(
            3,
            { is_preferred: true },
            "ja"
        );
    });

    it("splits the selected questions into a new meaning", async () => {
        mocked.splitConcept.mockResolvedValue(velocity);
        renderPage();

        await userEvent.click(await screen.findByText("velocity / speed"));
        await userEvent.click(await screen.findByLabelText(/速さとは？/));
        await userEvent.type(screen.getByLabelText("新しい意味の語(日本語)"), "速さ");
        await userEvent.type(screen.getByLabelText("新しい意味の語(英語)"), "speed");
        await userEvent.click(
            screen.getByRole("button", { name: "選んだ質問を新しい意味に分ける" })
        );

        expect(mocked.splitConcept).toHaveBeenCalledWith(
            7,
            {
                question_ids: [102],
                terms: [
                    { language: "ja", term: "速さ" },
                    { language: "en", term: "speed" },
                ],
            },
            "ja"
        );
    });
});
