// Accounts: own profile and history, admin user management ([64]).

import { AdminUser, CreateUserRequest } from "@/types/auth";
import { ContentLanguage, MyQuestionsResponse } from "@/types/question";
import { apiFetch, getUsersUrl } from "@/lib/api/client";

export async function fetchMyQuestions(
    page: number,
    size: number,
    lang: ContentLanguage,
): Promise<MyQuestionsResponse> {
    const params = new URLSearchParams({
        page: String(page),
        size: String(size),
        lang,
    });

    return apiFetch<MyQuestionsResponse>(
        `${getUsersUrl()}/me/questions?${params.toString()}`,
    );
}

export async function fetchMyProfile(): Promise<AdminUser> {
    return apiFetch<AdminUser>(`${getUsersUrl()}/me/profile`);
}

export async function deleteMyAccount(): Promise<void> {
    return apiFetch<void>(`${getUsersUrl()}/me`, {
        method: "DELETE",
    });
}

export async function getUsers(): Promise<AdminUser[]> {
    return apiFetch<AdminUser[]>(getUsersUrl());
}

export async function createUser(data: CreateUserRequest): Promise<AdminUser> {
    return apiFetch<AdminUser>(getUsersUrl(), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    });
}

export async function deleteUser(id: number): Promise<void> {
    return apiFetch<void>(`${getUsersUrl()}/${id}`, {
        method: "DELETE",
    });
}
