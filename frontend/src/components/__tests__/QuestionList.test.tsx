import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Question } from "@/types/question";

const navigation = {
    params: new URLSearchParams(),
    replace: vi.fn(),
    push: vi.fn(),
};
const stableRouter = {
    push: (...args: unknown[]) => navigation.push(...args),
    replace: (...args: unknown[]) => navigation.replace(...args),
};

vi.mock("next/navigation", () => ({
    useRouter: () => stableRouter,
    usePathname: () => "/",
    useSearchParams: () => navigation.params,
}));

vi.mock("@/lib/api", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@/lib/api")>();
    return { ...actual, fetchQuestions: vi.fn(), searchConcepts: vi.fn() };
});

import * as api from "@/lib/api";
import QuestionList from "@/components/QuestionList";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";

const mocked = vi.mocked(api);

function card(concepts: string[]): Question {
    return {
        id: 1,
        question: "速度ってなに？",
        answer: "向きを含む速さ。",
        language: "ja",
        provenance: "ORIGINAL",
        original_language: "ja",
        available_languages: ["ja"],
        texts: {},
        status: "APPROVED",
        source: "MANUAL",
        concepts,
        physics_level: 1,
        math_level: 1,
        retrieved_questions: [],
    };
}

function renderList() {
    render(
        <LanguageProvider>
            <QuestionList />
        </LanguageProvider>,
    );
}

beforeEach(() => {
    navigation.params = new URLSearchParams();
    mocked.fetchQuestions.mockReset();
    mocked.searchConcepts.mockReset();
    mocked.searchConcepts.mockResolvedValue([]);
});

describe("QuestionList cards", () => {
    it("shows each card's tags as links outside the card link", async () => {
        mocked.fetchQuestions.mockResolvedValue({
            items: [
                card(["ベクトル", "速さ", "変位", "単位時間", "符号", "向き"]),
            ],
            total: 1,
            page: 1,
            size: 30,
        });

        renderList();

        const chip = await screen.findByRole("link", { name: "ベクトル" });
        expect(chip.closest("a")).toBe(chip);
        expect(chip.parentElement?.closest("a")).toBeNull();
        // Five tags on a card, the rest behind "more".
        expect(
            screen.getByRole("button", { name: "ほか1件" }),
        ).toBeInTheDocument();
    });

    it("has no tag search box any more", async () => {
        mocked.fetchQuestions.mockResolvedValue({
            items: [card([])],
            total: 1,
            page: 1,
            size: 30,
        });

        renderList();

        await screen.findByText("速度ってなに？");
        // Pagination selects are comboboxes too; look for the old box itself.
        expect(screen.queryByLabelText(/絞り込む/)).not.toBeInTheDocument();
        expect(
            screen.queryByPlaceholderText(/日本語か英語で入力/)
        ).not.toBeInTheDocument();
    });
});
