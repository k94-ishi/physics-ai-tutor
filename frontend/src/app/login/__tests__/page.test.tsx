import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const searchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
    useSearchParams: () => searchParams,
}));

vi.mock("@/lib/auth/AuthContext", () => ({
    useAuth: () => ({ login: vi.fn() }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@/lib/api")>();
    return { ...actual, fetchAuthProviders: vi.fn() };
});

import * as api from "@/lib/api";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";
import LoginPage from "@/app/login/page";

const mocked = vi.mocked(api);

function renderPage() {
    return render(
        <LanguageProvider>
            <LoginPage />
        </LanguageProvider>
    );
}

beforeEach(() => {
    mocked.fetchAuthProviders.mockReset();
    searchParams.delete("error");
});

describe("LoginPage", () => {
    it("shows the Google button only when the backend offers it", async () => {
        mocked.fetchAuthProviders.mockResolvedValue({ password: true, google: true });

        renderPage();

        const link = await screen.findByRole("link", { name: "Googleでログイン" });
        expect(link).toHaveAttribute(
            "href",
            "http://api.test/api/v1/auth/google/login"
        );
        expect(screen.getByLabelText(/メールアドレス/)).toBeInTheDocument();
    });

    it("hides the Google button when Google Sign-In is not configured", async () => {
        mocked.fetchAuthProviders.mockResolvedValue({ password: true, google: false });

        renderPage();

        await waitFor(() => expect(mocked.fetchAuthProviders).toHaveBeenCalled());
        expect(
            screen.queryByRole("link", { name: "Googleでログイン" })
        ).not.toBeInTheDocument();
        expect(screen.getByLabelText(/メールアドレス/)).toBeInTheDocument();
    });

    it("explains a rejected Google sign-in from the error query parameter", async () => {
        mocked.fetchAuthProviders.mockResolvedValue({ password: true, google: true });
        searchParams.set("error", "account_exists");

        renderPage();

        expect(
            await screen.findByText(/パスワードで登録されています/)
        ).toBeInTheDocument();
    });
});
