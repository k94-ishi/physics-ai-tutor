import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MyQuestionsResponse } from "@/types/question";
import { User } from "@/types/auth";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn(), replace }),
}));

let authUser: User | null = { id: 5, role: "user" };

vi.mock("@/lib/auth/AuthContext", () => ({
    useAuth: () => ({ user: authUser, loading: false, refresh: vi.fn() }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@/lib/api")>();
    return { ...actual, fetchMyQuestions: vi.fn() };
});

import * as api from "@/lib/api";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";
import MyQuestionsPage from "@/app/me/questions/page";

const mocked = vi.mocked(api);

const RESPONSE: MyQuestionsResponse = {
    items: [
        {
            question_id: 11,
            question: "承認済みの質問",
            answer: "承認済みの回答",
            language: "ja",
            provenance: "ORIGINAL",
            status: "APPROVED",
            asked_at: "2026-10-28T01:00:00Z",
        },
        {
            question_id: 12,
            question: "未レビューの質問",
            answer: "未レビューの回答",
            language: "ja",
            provenance: "ORIGINAL",
            status: "UNREVIEWED",
            asked_at: "2026-10-28T00:30:00Z",
        },
        {
            question_id: 13,
            question: "却下された質問",
            answer: null,
            language: "ja",
            provenance: "ORIGINAL",
            status: "REJECTED",
            asked_at: "2026-10-28T00:00:00Z",
        },
    ],
    total: 3,
    page: 1,
    size: 20,
};

function renderPage() {
    return render(
        <LanguageProvider>
            <MyQuestionsPage />
        </LanguageProvider>
    );
}

beforeEach(() => {
    authUser = { id: 5, role: "user" };
    replace.mockReset();
    mocked.fetchMyQuestions.mockReset().mockResolvedValue(RESPONSE);
});

describe("MyQuestionsPage", () => {
    it("lists asks with status badges and answers", async () => {
        renderPage();

        expect(await screen.findByText("承認済みの質問")).toBeInTheDocument();
        expect(screen.getByText("承認済み")).toBeInTheDocument();
        expect(screen.getByText("未レビュー")).toBeInTheDocument();
        expect(screen.getByText("承認済みの回答")).toBeInTheDocument();

        // Only approved questions link to the public detail page.
        const detail = screen.getByRole("link", { name: "詳細を見る" });
        expect(detail).toHaveAttribute("href", "/questions/11");
    });

    it("shows a neutral notice instead of a rejected answer", async () => {
        renderPage();

        expect(await screen.findByText("却下された質問")).toBeInTheDocument();
        expect(
            screen.getByText(/先生の確認により取り下げられました/)
        ).toBeInTheDocument();
        expect(screen.queryByText("却下された回答")).not.toBeInTheDocument();
    });

    it("shows the empty message when there is no history", async () => {
        mocked.fetchMyQuestions.mockResolvedValue({
            items: [],
            total: 0,
            page: 1,
            size: 20,
        });

        renderPage();

        expect(
            await screen.findByText(/まだ質問の履歴がありません/)
        ).toBeInTheDocument();
    });

    it("redirects to login when signed out", async () => {
        authUser = null;

        renderPage();

        await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
        expect(mocked.fetchMyQuestions).not.toHaveBeenCalled();
    });
});
