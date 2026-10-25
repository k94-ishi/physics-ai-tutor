"use client";

import { ReactNode, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/AuthContext";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import LoadingState from "@/components/ui/LoadingState";
import StatusMessage from "@/components/ui/StatusMessage";

export default function AdminLayout({ children }: { children: ReactNode }) {
    const router = useRouter();
    const { user, loading } = useAuth();
    const { t } = useLanguage();

    useEffect(() => {
        if (!loading && !user) {
            router.replace("/login");
        }
    }, [loading, user, router]);

    if (loading || !user) {
        return <LoadingState label={t("adminLayout.checking")} />;
    }

    if (user.role !== "admin") {
        return (
            <StatusMessage
                variant="error"
                message={t("adminLayout.adminOnly")}
            />
        );
    }

    return <>{children}</>;
}
