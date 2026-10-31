"use client";

import { useLanguage } from "@/lib/i18n/LanguageContext";
import { showToast } from "@/components/ui/Toast";

type QuestionIdBadgeProps = {
    id: number;
};

/**
 * 質問IDを `#123` の形で表示し、クリックで数字だけをコピーする。
 * issue・eval・レビュー実行の出力はどれも質問をIDで指すので、一覧・編集・
 * 履歴のどこからでも同じ見た目でIDを確認・コピーできるようにする。
 */
export default function QuestionIdBadge({ id }: QuestionIdBadgeProps) {
    const { t } = useLanguage();

    const copy = async (event: React.MouseEvent) => {
        // カード全体がクリック可能なので、コピーだけを実行する。
        event.stopPropagation();
        event.preventDefault();

        try {
            await navigator.clipboard.writeText(String(id));
            showToast(t("admin.questionIdCopied", { id }));
        } catch {
            // クリップボードが使えない環境では表示だけで十分なので黙って無視する。
        }
    };

    return (
        <button
            type="button"
            onClick={copy}
            title={t("admin.questionIdCopy", { id })}
            aria-label={t("admin.questionIdCopy", { id })}
            className="shrink-0 cursor-pointer rounded-full bg-gray-100 px-2 py-0.5 font-mono text-xs font-medium text-gray-600 hover:bg-gray-200"
        >
            #{id}
        </button>
    );
}
