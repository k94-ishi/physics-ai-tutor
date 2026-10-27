export type UserRole = "admin" | "user";

export type AuthProvider = "password" | "google";

export type AuthProviders = {
    password: boolean;
    google: boolean;
};

export type User = {
    id: number;
    role: UserRole;
};

export type LoginRequest = {
    email: string;
    password: string;
};

export type AdminUser = {
    id: number;
    email: string;
    role: UserRole;
    auth_provider: AuthProvider;
    created_at: string;
};

export type CreateUserRequest = {
    email: string;
    password: string;
    role: UserRole;
};
