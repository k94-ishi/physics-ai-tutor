export type UserRole = "admin" | "user";

export type User = {
    id: number;
    role: UserRole;
};

export type LoginRequest = {
    email: string;
    password: string;
};
