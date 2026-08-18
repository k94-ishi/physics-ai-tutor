"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/AuthContext";
import { showToast } from "@/components/ui/Toast";
import { Language, useLanguage } from "@/lib/i18n/LanguageContext";

export default function Header() {
    const router = useRouter();
    const { user, logout } = useAuth();
    const { language, setLanguage, t } = useLanguage();

    const handleLogout = async () => {
        try {
            await logout();
            showToast(t("header.logoutSuccess"));
            router.push("/");
        } catch (error) {
            console.error(error);
            showToast(t("header.logoutFailed"), "error");
        }
    };

    return (
        <header className="border-b border-gray-200 bg-white">
            <div className="mx-auto flex w-full max-w-4xl items-center justify-between px-3 py-3">
                <Link href="/" className="text-lg font-bold text-gray-900">
                    Physics AI Tutor
                </Link>

                <nav className="flex items-center gap-4 text-sm">
                    <Link
                        href="/"
                        className="text-gray-600 hover:text-gray-900"
                    >
                        {t("header.questionList")}
                    </Link>

                    {user?.role === "admin" && (
                        <>
                            <Link
                                href="/admin/questions"
                                className="text-gray-600 hover:text-gray-900"
                            >
                                {t("header.questionManagement")}
                            </Link>

                            <Link
                                href="/admin/users"
                                className="text-gray-600 hover:text-gray-900"
                            >
                                {t("header.userManagement")}
                            </Link>
                        </>
                    )}

                    {user ? (
                        <button
                            type="button"
                            onClick={handleLogout}
                            className="text-gray-600 hover:text-gray-900"
                        >
                            {t("header.logout")}
                        </button>
                    ) : (
                        <Link
                            href="/login"
                            className="text-gray-600 hover:text-gray-900"
                        >
                            {t("header.adminLogin")}
                        </Link>
                    )}

                    <label className="flex items-center gap-1.5 text-gray-600">
                        Language:
                        <select
                            value={language}
                            onChange={(e) =>
                                setLanguage(e.target.value as Language)
                            }
                            className="rounded-md border border-gray-300 bg-white px-1.5 py-1 text-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        >
                            <option value="ja">日本語</option>
                            <option value="en">English (under development)</option>
                        </select>
                    </label>
                </nav>
            </div>
        </header>
    );
}
