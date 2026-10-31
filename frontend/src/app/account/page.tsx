"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { deleteMyAccount, fetchMyProfile } from "@/lib/api";
import { AdminUser } from "@/types/auth";
import { useAuth } from "@/lib/auth/AuthContext";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import LoadingState from "@/components/ui/LoadingState";
import StatusMessage from "@/components/ui/StatusMessage";
import { showToast } from "@/components/ui/Toast";
import { useLanguage } from "@/lib/i18n/LanguageContext";

export default function AccountPage() {
    const router = useRouter();
    const { user, loading: authLoading, refresh } = useAuth();
    const { language, t } = useLanguage();
    const [profile, setProfile] = useState<AdminUser | null>(null);
    const [loadError, setLoadError] = useState(false);
    const [confirming, setConfirming] = useState(false);
    const [deleting, setDeleting] = useState(false);

    useEffect(() => {
        if (!authLoading && !user) {
            router.replace("/login");
        }
    }, [authLoading, user, router]);

    const loadProfile = useCallback(async () => {
        setLoadError(false);

        try {
            setProfile(await fetchMyProfile());
        } catch (error) {
            console.error(error);
            setLoadError(true);
        }
    }, []);

    useEffect(() => {
        if (user) {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            loadProfile();
        }
    }, [user, loadProfile]);

    const handleDelete = async () => {
        setDeleting(true);

        try {
            await deleteMyAccount();
            await refresh();
            showToast(t("account.deleted"));
            router.push("/");
        } catch (error) {
            console.error(error);
            showToast(t("account.deleteFailed"), "error");
            setDeleting(false);
            setConfirming(false);
        }
    };

    if (authLoading || !user) {
        return <LoadingState />;
    }

    if (loadError) {
        return (
            <StatusMessage
                variant="error"
                message={t("account.fetchFailed")}
                onRetry={loadProfile}
            />
        );
    }

    if (profile === null) {
        return <LoadingState />;
    }

    return (
        <main className="mx-auto flex max-w-sm flex-col gap-6">
            <h1 className="text-2xl font-bold text-gray-900">
                {t("account.title")}
            </h1>

            <Card className="flex flex-col gap-3">
                <dl className="flex flex-col gap-3 text-sm">
                    <div className="flex flex-col gap-0.5">
                        <dt className="text-gray-500">
                            {t("account.emailLabel")}
                        </dt>
                        <dd className="text-gray-900">{profile.email}</dd>
                    </div>
                    <div className="flex flex-col gap-0.5">
                        <dt className="text-gray-500">
                            {t("account.providerLabel")}
                        </dt>
                        <dd className="text-gray-900">
                            {profile.auth_provider === "google"
                                ? t("users.providerGoogle")
                                : t("users.providerPassword")}
                        </dd>
                    </div>
                    <div className="flex flex-col gap-0.5">
                        <dt className="text-gray-500">
                            {t("account.registeredLabel")}
                        </dt>
                        <dd className="text-gray-900">
                            {new Date(profile.created_at).toLocaleDateString(
                                language === "ja" ? "ja-JP" : "en-US"
                            )}
                        </dd>
                    </div>
                </dl>
            </Card>

            <Card className="flex flex-col gap-3">
                <h2 className="text-lg font-semibold text-gray-900">
                    {t("account.deleteHeading")}
                </h2>

                {profile.role === "admin" ? (
                    <p className="text-sm text-gray-600">
                        {t("account.adminNote")}
                    </p>
                ) : (
                    <>
                        <p className="text-sm text-gray-600">
                            {t("account.deleteDescription")}
                        </p>
                        <Button
                            variant="danger"
                            className="self-start"
                            onClick={() => setConfirming(true)}
                        >
                            {t("account.deleteButton")}
                        </Button>
                    </>
                )}
            </Card>

            <ConfirmDialog
                open={confirming}
                title={t("account.confirmDelete")}
                description={profile.email}
                confirming={deleting}
                onConfirm={handleDelete}
                onCancel={() => setConfirming(false)}
            />
        </main>
    );
}
