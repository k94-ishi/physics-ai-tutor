"use client";

import Link from "next/link";
import Card from "@/components/ui/Card";
import { useLanguage } from "@/lib/i18n/LanguageContext";

/** Entry page for owner-side management tools (data checks, validations). */
export default function AdminManagePage() {
    const { t } = useLanguage();

    return (
        <main className="flex flex-col gap-6">
            <div className="flex flex-col gap-2">
                <h1 className="text-2xl font-bold text-gray-900">{t("manage.title")}</h1>
                <p className="text-sm text-gray-600">{t("manage.intro")}</p>
            </div>

            <Card className="flex flex-col gap-1">
                <Link href="/admin/manage/levels" className="font-medium text-blue-600 hover:underline">
                    {t("levelsReview.title")}
                </Link>
                <p className="text-sm text-gray-600">{t("manage.levelsHint")}</p>
            </Card>
        </main>
    );
}
