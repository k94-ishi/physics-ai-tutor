import Link from "next/link";

export default function Header() {
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

                    <Link
                        href="/admin/questions"
                        className="text-gray-600 hover:text-gray-900"
                    >
                        管理画面
                    </Link>
                </nav>
            </div>
        </header>
    );
}
