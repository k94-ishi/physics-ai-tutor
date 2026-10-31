import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api";

vi.mock("@/lib/api", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@/lib/api")>();
    return {
        ...actual,
        fetchCurrentUser: vi.fn(),
        login: vi.fn(),
        logout: vi.fn(),
    };
});

import * as api from "@/lib/api";
import { AuthProvider, useAuth } from "@/lib/auth/AuthContext";

const mocked = vi.mocked(api);
const ADMIN = { id: 1, role: "admin" as const };

function wrapper({ children }: { children: React.ReactNode }) {
    return <AuthProvider>{children}</AuthProvider>;
}

beforeEach(() => {
    mocked.fetchCurrentUser.mockReset();
    mocked.login.mockReset();
    mocked.logout.mockReset();
});

describe("AuthProvider", () => {
    it("loads the current user on mount", async () => {
        mocked.fetchCurrentUser.mockResolvedValue(ADMIN);

        const { result } = renderHook(() => useAuth(), { wrapper });

        expect(result.current.loading).toBe(true);
        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.user).toEqual(ADMIN);
    });

    it("treats 401 as logged out without logging an error", async () => {
        mocked.fetchCurrentUser.mockRejectedValue(new ApiError(401, "unauthorized"));
        const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

        const { result } = renderHook(() => useAuth(), { wrapper });

        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.user).toBeNull();
        expect(errorSpy).not.toHaveBeenCalled();
    });

    it("logs unexpected errors but still finishes loading", async () => {
        mocked.fetchCurrentUser.mockRejectedValue(new ApiError(500, "boom"));
        const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

        const { result } = renderHook(() => useAuth(), { wrapper });

        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.user).toBeNull();
        expect(errorSpy).toHaveBeenCalledOnce();
    });

    it("login stores the returned user and logout clears it", async () => {
        mocked.fetchCurrentUser.mockRejectedValue(new ApiError(401, "unauthorized"));
        mocked.login.mockResolvedValue(ADMIN);
        mocked.logout.mockResolvedValue(undefined);

        const { result } = renderHook(() => useAuth(), { wrapper });
        await waitFor(() => expect(result.current.loading).toBe(false));

        await act(() => result.current.login("a@example.com", "secret12"));
        expect(result.current.user).toEqual(ADMIN);
        expect(mocked.login).toHaveBeenCalledWith({
            email: "a@example.com",
            password: "secret12",
        });

        await act(() => result.current.logout());
        expect(result.current.user).toBeNull();
    });

    it("throws when used outside the provider", () => {
        expect(() => renderHook(() => useAuth())).toThrow(
            "useAuth must be used within an AuthProvider"
        );
    });
});
