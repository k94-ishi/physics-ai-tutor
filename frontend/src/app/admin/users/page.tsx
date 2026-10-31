"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { getUsers, deleteUser } from "@/lib/api";
import { AdminUser } from "@/types/auth";
import Card from "@/components/ui/Card";
import Button, { buttonClassName } from "@/components/ui/Button";
import LoadingState from "@/components/ui/LoadingState";
import StatusMessage from "@/components/ui/StatusMessage";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { showToast } from "@/components/ui/Toast";
import { useLanguage } from "@/lib/i18n/LanguageContext";

export default function AdminUsersPage() {
    const { language, t } = useLanguage();
    const [users, setUsers] = useState<AdminUser[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);
    const [deleteTarget, setDeleteTarget] = useState<AdminUser | null>(null);
    const [deleting, setDeleting] = useState(false);

    const loadUsers = useCallback(async () => {
        setLoading(true);
        setError(false);

        try {
            const data = await getUsers();
            setUsers(data);
        } catch (error) {
            console.error(error);
            setError(true);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        loadUsers();
    }, [loadUsers]);

    const handleConfirmDelete = async () => {
        if (!deleteTarget) {
            return;
        }

        setDeleting(true);

        try {
            await deleteUser(deleteTarget.id);
            await loadUsers();
            showToast(t("users.deleted"));
            setDeleteTarget(null);
        } catch (error) {
            console.error(error);
            showToast(t("users.deleteFailed"), "error");
        } finally {
            setDeleting(false);
        }
    };

    if (loading) {
        return <LoadingState />;
    }

    return (
        <main className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-gray-900">
                    {t("users.title")}
                </h1>

                <Link
                    href="/admin/users/new"
                    className={buttonClassName("primary")}
                >
                    {t("users.newButton")}
                </Link>
            </div>

            {error && (
                <StatusMessage
                    variant="error"
                    message={t("users.fetchFailed")}
                    onRetry={loadUsers}
                />
            )}

            {!error && users.length === 0 && (
                <StatusMessage message={t("users.empty")} />
            )}

            {!error && users.length > 0 && (
                <ul className="flex flex-col gap-3">
                    {users.map((user) => (
                        <li key={user.id}>
                            <Card className="flex items-center justify-between gap-4">
                                <div className="flex flex-col gap-1">
                                    <span className="text-gray-900">
                                        {user.email}
                                    </span>
                                    <span className="text-xs text-gray-500">
                                        {user.role === "admin"
                                            ? t("users.roleAdmin")
                                            : t("users.roleUser")}
                                        {` ・ ${t("users.registeredOn")}: `}
                                        {new Date(user.created_at).toLocaleDateString(
                                            language === "ja" ? "ja-JP" : "en-US"
                                        )}
                                    </span>
                                </div>

                                <Button
                                    variant="danger"
                                    onClick={() => setDeleteTarget(user)}
                                >
                                    {t("common.delete")}
                                </Button>
                            </Card>
                        </li>
                    ))}
                </ul>
            )}

            <ConfirmDialog
                open={deleteTarget !== null}
                title={t("users.confirmDelete")}
                description={deleteTarget?.email}
                confirming={deleting}
                onConfirm={handleConfirmDelete}
                onCancel={() => setDeleteTarget(null)}
            />
        </main>
    );
}
