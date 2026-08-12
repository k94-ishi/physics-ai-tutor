"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/AuthContext";
import { showToast } from "@/components/ui/Toast";

export default function Header() {
    const router = useRouter();
    const { user, logout } = useAuth();

    const handleLogout = async () => {
        try {
            await logout();
            showToast("ログアウトしました。");
            router.push("/");
        } catch (error) {
            console.error(error);
            showToast("ログアウトに失敗しました。", "error");
        }
    };

    return (
        <header className="border-b border-gray-200 bg-white">
            <div className="mx-auto flex w-full max-w-4xl items-center justify-between px-4 py-4">
                <Link href="/" className="text-lg font-bold text-gray-900">
                    Physics AI Tutor
                </Link>

                <nav className="flex items-center gap-4 text-sm">
                    <Link
                        href="/"
                        className="text-gray-600 hover:text-gray-900"
                    >
                        質問一覧
                    </Link>

                    {user?.role === "admin" && (
                        <Link
                            href="/admin/questions"
                            className="text-gray-600 hover:text-gray-900"
                        >
                            管理画面
                        </Link>
                    )}

                    {user ? (
                        <button
                            type="button"
                            onClick={handleLogout}
                            className="text-gray-600 hover:text-gray-900"
                        >
                            ログアウト
                        </button>
                    ) : (
                        <Link
                            href="/login"
                            className="text-gray-600 hover:text-gray-900"
                        >
                            ログイン
                        </Link>
                    )}
                </nav>
            </div>
        </header>
    );
}
