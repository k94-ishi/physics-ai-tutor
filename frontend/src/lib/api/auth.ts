// Login, logout and the current session ([64]).

import { AuthProviders, LoginRequest, User } from "@/types/auth";
import { apiFetch, getAuthUrl, getUsersUrl } from "@/lib/api/client";

export async function login(data: LoginRequest): Promise<User> {
    return apiFetch<User>(`${getAuthUrl()}/login`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    });
}

export async function fetchAuthProviders(): Promise<AuthProviders> {
    return apiFetch<AuthProviders>(`${getAuthUrl()}/providers`);
}

// A plain navigation: the backend redirects the browser to Google.

export function getGoogleLoginUrl(): string {
    return `${getAuthUrl()}/google/login`;
}

export async function logout(): Promise<void> {
    return apiFetch<void>(`${getAuthUrl()}/logout`, {
        method: "POST",
    });
}

export async function fetchCurrentUser(): Promise<User> {
    return apiFetch<User>(`${getUsersUrl()}/me`);
}
