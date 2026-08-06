import Link from "next/link";
import { buttonClassName } from "@/components/ui/Button";

export default function NotFound() {
    return (
        <main className="flex flex-col items-start gap-4">
            <h1 className="text-xl font-bold text-gray-900">
                ページが見つかりません
            </h1>

            <p className="text-sm text-gray-600">
                お探しのページは存在しないか、削除された可能性があります。
            </p>

            <Link href="/" className={buttonClassName("primary")}>
                トップへ戻る
            </Link>
        </main>
    );
}
