import Link from "next/link";

export default function NotFound() {
    return (
        <main>
            <h1>ページが見つかりません</h1>
            <p>お探しのページは存在しないか、削除された可能性があります。</p>
            <Link href="/">トップへ戻る</Link>
        </main>
    );
}
