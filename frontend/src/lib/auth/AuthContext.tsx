"use client";

import {
    createContext,
    ReactNode,
    useCallback,
    useContext,
    useEffect,
    useState,
} from "react";
import {
    ApiError,
    fetchCurrentUser,
    login as apiLogin,
    logout as apiLogout,
} from "@/lib/api";
import { User } from "@/types/auth";

type AuthContextValue = {
    user: User | null;
    loading: boolean;
    login: (email: string, password: string) => Promise<User>;
    logout: () => Promise<void>;
    refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    const refresh = useCallback(async () => {
        try {
            const currentUser = await fetchCurrentUser();
            setUser(currentUser);
        } catch (error) {
            // 未ログイン(401)はエラーではなく通常の状態として扱う
            if (!(error instanceof ApiError && error.status === 401)) {
                console.error(error);
            }
            setUser(null);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        refresh();
    }, [refresh]);

    const login = useCallback(async (email: string, password: string) => {
        const loggedInUser = await apiLogin({ email, password });
        setUser(loggedInUser);
        return loggedInUser;
    }, []);

    const logout = useCallback(async () => {
        await apiLogout();
        setUser(null);
    }, []);

    return (
        <AuthContext.Provider value={{ user, loading, login, logout, refresh }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth(): AuthContextValue {
    const context = useContext(AuthContext);

    if (context === undefined) {
        throw new Error("useAuth must be used within an AuthProvider");
    }

    return context;
}
