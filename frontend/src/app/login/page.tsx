"use client";

import { Suspense, SyntheticEvent, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth/AuthContext";
import { fetchAuthProviders, getGoogleLoginUrl } from "@/lib/api";
import { AuthProviders } from "@/types/auth";
import Card from "@/components/ui/Card";
import TextField from "@/components/ui/TextField";
import Button, { buttonClassName } from "@/components/ui/Button";
import StatusMessage from "@/components/ui/StatusMessage";
import LoadingState from "@/components/ui/LoadingState";
import { useLanguage } from "@/lib/i18n/LanguageContext";

// Error codes the backend appends when the Google callback fails.
const GOOGLE_ERROR_KEYS = {
    google_failed: "login.googleFailed",
    account_exists: "login.accountExists",
} as const;

type GoogleErrorCode = keyof typeof GOOGLE_ERROR_KEYS;

function isGoogleErrorCode(value: string | null): value is GoogleErrorCode {
    return value !== null && value in GOOGLE_ERROR_KEYS;
}

export default function LoginPage() {
    // useSearchParams requires a Suspense boundary for static rendering.
    return (
        <Suspense fallback={<LoadingState />}>
            <LoginContent />
        </Suspense>
    );
}

function LoginContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { login } = useAuth();
    const { t } = useLanguage();

    const [providers, setProviders] = useState<AuthProviders | null>(null);
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(false);

    const googleError = searchParams.get("error");

    useEffect(() => {
        let cancelled = false;

        fetchAuthProviders()
            .then((data) => {
                if (!cancelled) {
                    // eslint-disable-next-line react-hooks/set-state-in-effect
                    setProviders(data);
                }
            })
            .catch((err) => {
                console.error(err);
            });

        return () => {
            cancelled = true;
        };
    }, []);

    const handleSubmit = async (e: SyntheticEvent<HTMLFormElement>) => {
        e.preventDefault();

        setLoading(true);
        setError(false);

        try {
            await login(email, password);
            router.push("/");
        } catch (err) {
            console.error(err);
            setError(true);
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="mx-auto flex max-w-sm flex-col gap-6">
            <h1 className="text-2xl font-bold text-gray-900">
                {t("login.title")}
            </h1>

            {isGoogleErrorCode(googleError) && (
                <StatusMessage
                    variant="error"
                    message={t(GOOGLE_ERROR_KEYS[googleError])}
                />
            )}

            {providers?.google && (
                <Card className="flex flex-col gap-4">
                    <h2 className="text-lg font-semibold text-gray-900">
                        {t("login.studentHeading")}
                    </h2>
                    <p className="text-sm text-gray-600">
                        {t("login.studentHint")}
                    </p>
                    <a
                        href={getGoogleLoginUrl()}
                        className={buttonClassName("primary", "w-full")}
                    >
                        {t("login.withGoogle")}
                    </a>
                </Card>
            )}

            <Card>
                <h2 className="mb-4 text-lg font-semibold text-gray-900">
                    {t("login.adminHeading")}
                </h2>

                <form
                    onSubmit={handleSubmit}
                    noValidate
                    className="flex flex-col gap-5"
                >
                    <TextField
                        id="email"
                        label={t("login.email")}
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        autoComplete="username"
                    />

                    <TextField
                        id="password"
                        label={t("login.password")}
                        type="password"
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        autoComplete="current-password"
                    />

                    {error && (
                        <StatusMessage
                            variant="error"
                            message={t("login.invalidCredentials")}
                        />
                    )}

                    <Button type="submit" disabled={loading} className="self-start">
                        {loading ? t("login.loggingIn") : t("header.adminLogin")}
                    </Button>
                </form>
            </Card>
        </main>
    );
}
