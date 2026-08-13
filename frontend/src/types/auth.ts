export type UserRole = "admin" | "user";

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
    created_at: string;
};

export type CreateUserRequest = {
    email: string;
    password: string;
    role: UserRole;
};
