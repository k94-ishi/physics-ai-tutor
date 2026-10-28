"use client";

import { ReactNode } from "react";
import Card from "@/components/ui/Card";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { TranslationKey } from "@/lib/i18n/translations";

const LAST_UPDATED = "2026-10-28";

// Replace with a monitored contact address before publishing the Google
// OAuth consent screen; until then the repository's issue tracker is the
// only public channel that exists.
const CONTACT_URL = "https://github.com/k94-ishi/physics-ai-tutor/issues";

function Section({
    headingKey,
    children,
}: {
    headingKey: TranslationKey;
    children: ReactNode;
}) {
    const { t } = useLanguage();

    return (
        <Card className="flex flex-col gap-2">
            <h2 className="text-lg font-semibold text-gray-900">
                {t(headingKey)}
            </h2>
            {children}
        </Card>
    );
}

function Paragraphs({ keys }: { keys: TranslationKey[] }) {
    const { t } = useLanguage();

    return (
        <>
            {keys.map((key) => (
                <p key={key} className="text-sm leading-relaxed text-gray-700">
                    {t(key)}
                </p>
            ))}
        </>
    );
}

function Items({ keys }: { keys: TranslationKey[] }) {
    const { t } = useLanguage();

    return (
        <ul className="flex list-disc flex-col gap-1.5 pl-5">
            {keys.map((key) => (
                <li key={key} className="text-sm leading-relaxed text-gray-700">
                    {t(key)}
                </li>
            ))}
        </ul>
    );
}

export default function PrivacyPage() {
    const { t } = useLanguage();

    return (
        <main className="mx-auto flex max-w-2xl flex-col gap-4">
            <div className="flex flex-col gap-1">
                <h1 className="text-2xl font-bold text-gray-900">
                    {t("privacy.title")}
                </h1>
                <p className="text-xs text-gray-500">
                    {t("privacy.lastUpdated", { date: LAST_UPDATED })}
                </p>
            </div>

            <p className="text-sm leading-relaxed text-gray-700">
                {t("privacy.intro")}
            </p>

            <Section headingKey="privacy.collect.heading">
                <Items
                    keys={[
                        "privacy.collect.account",
                        "privacy.collect.questions",
                        "privacy.collect.usage",
                        "privacy.collect.cookies",
                    ]}
                />
            </Section>

            <Section headingKey="privacy.notCollect.heading">
                <Paragraphs keys={["privacy.notCollect.body"]} />
            </Section>

            <Section headingKey="privacy.purpose.heading">
                <Items
                    keys={[
                        "privacy.purpose.login",
                        "privacy.purpose.abuse",
                        "privacy.purpose.content",
                    ]}
                />
            </Section>

            <Section headingKey="privacy.thirdParties.heading">
                <Paragraphs keys={["privacy.thirdParties.intro"]} />
                <Items
                    keys={[
                        "privacy.thirdParties.google",
                        "privacy.thirdParties.llm",
                        "privacy.thirdParties.hosting",
                    ]}
                />
            </Section>

            <Section headingKey="privacy.retention.heading">
                <Paragraphs keys={["privacy.retention.body"]} />
            </Section>

            <Section headingKey="privacy.deletion.heading">
                <Paragraphs keys={["privacy.deletion.body"]} />
            </Section>

            <Section headingKey="privacy.contact.heading">
                <Paragraphs keys={["privacy.contact.body"]} />
                <a
                    href={CONTACT_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue-600 underline hover:text-blue-800"
                >
                    {t("privacy.contact.linkLabel")}
                </a>
            </Section>

            <Section headingKey="privacy.changes.heading">
                <Paragraphs keys={["privacy.changes.body"]} />
            </Section>
        </main>
    );
}
