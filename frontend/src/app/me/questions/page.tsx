"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { fetchMyQuestions } from "@/lib/api";
import { MyQuestionEntry, QuestionStatus } from "@/types/question";
import { useAuth } from "@/lib/auth/AuthContext";
import Card from "@/components/ui/Card";
import LoadingState from "@/components/ui/LoadingState";
import MarkdownContent from "@/components/ui/MarkdownContent";
import Pagination from "@/components/ui/Pagination";
import StatusMessage from "@/components/ui/StatusMessage";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { TranslationKey } from "@/lib/i18n/translations";

const STATUS_LABEL_KEYS: Record<QuestionStatus, TranslationKey> = {
    UNREVIEWED: "admin.status.unreviewed",
    APPROVED: "admin.status.approved",
    REJECTED: "admin.status.rejected",
};

const STATUS_BADGE_CLASSES: Record<QuestionStatus, string> = {
    UNREVIEWED: "bg-yellow-100 text-yellow-800",
    APPROVED: "bg-green-100 text-green-800",
    REJECTED: "bg-gray-200 text-gray-600",
};

function StatusBadge({ status }: { status: QuestionStatus }) {
    const { t } = useLanguage();

    return (
        <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE_CLASSES[status]}`}
        >
            {t(STATUS_LABEL_KEYS[status])}
        </span>
    );
}

function Entry({ entry }: { entry: MyQuestionEntry }) {
    const { language, t } = useLanguage();

    return (
        <Card className="flex flex-col gap-3">
            <div className="flex items-start justify-between gap-3">
                <p className="font-medium text-gray-900">{entry.question}</p>
                <StatusBadge status={entry.status} />
            </div>

            {entry.status === "REJECTED" ? (
                <p className="text-sm text-gray-600">
                    {t("myQuestions.rejectedNotice")}
                </p>
            ) : (
                entry.answer !== null && (
                    <MarkdownContent content={entry.answer} />
                )
            )}

            <div className="flex items-center justify-between text-xs text-gray-500">
                <span>
                    {t("myQuestions.askedOn")}:{" "}
                    {new Date(entry.asked_at).toLocaleString(
                        language === "ja" ? "ja-JP" : "en-US"
                    )}
                </span>

                {entry.status === "APPROVED" && (
                    <Link
                        href={`/questions/${entry.question_id}`}
                        className="text-blue-600 underline hover:text-blue-800"
                    >
                        {t("myQuestions.viewDetail")}
                    </Link>
                )}
            </div>
        </Card>
    );
}

export default function MyQuestionsPage() {
    const router = useRouter();
    const { user, loading: authLoading } = useAuth();
    const { language, t } = useLanguage();
    const [entries, setEntries] = useState<MyQuestionEntry[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [size, setSize] = useState(20);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        if (!authLoading && !user) {
            router.replace("/login");
        }
    }, [authLoading, user, router]);

    const load = useCallback(async () => {
        setLoading(true);
        setError(false);

        try {
            const data = await fetchMyQuestions(page, size, language);
            setEntries(data.items);
            setTotal(data.total);
        } catch (error) {
            console.error(error);
            setError(true);
        } finally {
            setLoading(false);
        }
    }, [page, size, language]);

    useEffect(() => {
        if (user) {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            load();
        }
    }, [user, load]);

    if (authLoading || !user || loading) {
        return <LoadingState />;
    }

    return (
        <main className="flex flex-col gap-6">
            <h1 className="text-2xl font-bold text-gray-900">
                {t("myQuestions.title")}
            </h1>

            {error && (
                <StatusMessage
                    variant="error"
                    message={t("myQuestions.fetchFailed")}
                    onRetry={load}
                />
            )}

            {!error && entries.length === 0 && (
                <StatusMessage message={t("myQuestions.empty")} />
            )}

            {!error && entries.length > 0 && (
                <>
                    <ul className="flex flex-col gap-3">
                        {entries.map((entry, index) => (
                            <li key={`${entry.question_id}-${entry.asked_at}-${index}`}>
                                <Entry entry={entry} />
                            </li>
                        ))}
                    </ul>

                    <Pagination
                        page={page}
                        size={size}
                        total={total}
                        onPageChange={setPage}
                        onSizeChange={(next) => {
                            setSize(next);
                            setPage(1);
                        }}
                        sizeOptions={[20, 50, 100]}
                    />
                </>
            )}
        </main>
    );
}
