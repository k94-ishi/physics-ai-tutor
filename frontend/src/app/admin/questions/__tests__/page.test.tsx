import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Question } from "@/types/question";

const navigation = { params: new URLSearchParams(), replace: vi.fn(), push: vi.fn() };
const stableRouter = {
    push: (...args: unknown[]) => navigation.push(...args),
    replace: (...args: unknown[]) => navigation.replace(...args),
};

vi.mock("next/navigation", () => ({
    useRouter: () => stableRouter,
    usePathname: () => "/admin/questions",
    useSearchParams: () => navigation.params,
}));

vi.mock("@/lib/api", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@/lib/api")>();
    return { ...actual, fetchQuestions: vi.fn() };
});

import * as api from "@/lib/api";
import AdminQuestionsPage from "@/app/admin/questions/page";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";

const mocked = vi.mocked(api);

const QUESTION: Question = {
    id: 54,
    question: "速度ってなに？",
    answer: "向きを含む速さ。",
    language: "ja",
    provenance: "ORIGINAL",
    original_language: "ja",
    available_languages: ["ja"],
    texts: {},
    status: "APPROVED",
    source: "MANUAL",
    concepts: ["ベクトル", "速さ"],
    physics_level: 1,
    math_level: 1,
    retrieved_questions: [],
    generation: null,
    ai_review: null,
};

function renderPage() {
    render(
        <LanguageProvider>
            <AdminQuestionsPage />
        </LanguageProvider>
    );
}

beforeEach(() => {
    navigation.params = new URLSearchParams();
    navigation.replace.mockReset();
    mocked.fetchQuestions.mockReset();
    mocked.fetchQuestions.mockResolvedValue({
        items: [QUESTION],
        total: 1,
        page: 1,
        size: 30,
    });
});

describe("admin queue tag filter", () => {
    it("clicking a card's tag puts it in the URL and back on page 1", async () => {
        renderPage();

        await userEvent.click(await screen.findByRole("button", { name: "ベクトル" }));

        const url = String(navigation.replace.mock.calls.at(-1)?.[0]);
        expect(decodeURIComponent(url)).toContain("concept=ベクトル");
        expect(url).not.toContain("page=");
    });

    it("filters on the server and offers a way out", async () => {
        navigation.params = new URLSearchParams({ concept: "ベクトル", page: "2" });

        renderPage();

        await waitFor(() =>
            expect(mocked.fetchQuestions).toHaveBeenCalledWith(
                expect.objectContaining({ concept: "ベクトル", page: 2 })
            )
        );
        expect(screen.getByText("タグ「ベクトル」の質問")).toBeInTheDocument();
        await userEvent.click(screen.getByRole("button", { name: "絞り込みを解除" }));
        expect(String(navigation.replace.mock.calls.at(-1)?.[0])).not.toContain(
            "concept="
        );
    });
});
