"use client";

import { ReactNode, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/AuthContext";
import LoadingState from "@/components/ui/LoadingState";
import StatusMessage from "@/components/ui/StatusMessage";

export default function AdminLayout({ children }: { children: ReactNode }) {
    const router = useRouter();
    const { user, loading } = useAuth();

    useEffect(() => {
        if (!loading && !user) {
            router.replace("/login");
        }
    }, [loading, user, router]);

    if (loading || !user) {
        return <LoadingState label="確認中..." />;
    }

    if (user.role !== "admin") {
        return (
            <StatusMessage
                variant="error"
                message="このページには管理者権限が必要です。"
            />
        );
    }

    return <>{children}</>;
}
