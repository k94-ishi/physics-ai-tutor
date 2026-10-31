import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AdminUser, User } from "@/types/auth";

const push = vi.fn();
const replace = vi.fn();

vi.mock("next/navigation", () => ({
    useRouter: () => ({ push, replace }),
}));

let authUser: User | null = { id: 5, role: "user" };
const refresh = vi.fn();

vi.mock("@/lib/auth/AuthContext", () => ({
    useAuth: () => ({ user: authUser, loading: false, refresh }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@/lib/api")>();
    return {
        ...actual,
        fetchMyProfile: vi.fn(),
        deleteMyAccount: vi.fn(),
    };
});

import * as api from "@/lib/api";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";
import AccountPage from "@/app/account/page";

const mocked = vi.mocked(api);

const PROFILE: AdminUser = {
    id: 5,
    email: "student@gmail.com",
    role: "user",
    auth_provider: "google",
    created_at: "2026-10-28T00:00:00Z",
};

function renderPage() {
    return render(
        <LanguageProvider>
            <AccountPage />
        </LanguageProvider>
    );
}

beforeEach(() => {
    authUser = { id: 5, role: "user" };
    push.mockReset();
    replace.mockReset();
    refresh.mockReset().mockResolvedValue(undefined);
    mocked.fetchMyProfile.mockReset().mockResolvedValue(PROFILE);
    mocked.deleteMyAccount.mockReset().mockResolvedValue(undefined);
});

describe("AccountPage", () => {
    it("shows the profile and deletes the account after confirmation", async () => {
        const user = userEvent.setup();
        renderPage();

        expect(await screen.findByText("student@gmail.com")).toBeInTheDocument();
        expect(screen.getByText("Google")).toBeInTheDocument();

        await user.click(
            screen.getByRole("button", { name: "アカウントを削除" })
        );
        await user.click(screen.getByRole("button", { name: "削除" }));

        await waitFor(() => expect(mocked.deleteMyAccount).toHaveBeenCalled());
        expect(refresh).toHaveBeenCalled();
        expect(push).toHaveBeenCalledWith("/");
    });

    it("offers no delete button to admins", async () => {
        authUser = { id: 1, role: "admin" };
        mocked.fetchMyProfile.mockResolvedValue({
            ...PROFILE,
            id: 1,
            role: "admin",
            auth_provider: "password",
        });

        renderPage();

        await screen.findByText("student@gmail.com");
        expect(
            screen.queryByRole("button", { name: "アカウントを削除" })
        ).not.toBeInTheDocument();
        expect(
            screen.getByText(/管理者アカウントはここからは削除できません/)
        ).toBeInTheDocument();
    });

    it("redirects to the login page when signed out", async () => {
        authUser = null;

        renderPage();

        await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
        expect(mocked.fetchMyProfile).not.toHaveBeenCalled();
    });
});
