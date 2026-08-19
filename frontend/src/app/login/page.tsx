"use client";

import { SyntheticEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/AuthContext";
import Card from "@/components/ui/Card";
import TextField from "@/components/ui/TextField";
import Button from "@/components/ui/Button";
import StatusMessage from "@/components/ui/StatusMessage";
import { useLanguage } from "@/lib/i18n/LanguageContext";

export default function LoginPage() {
    const router = useRouter();
    const { login } = useAuth();
    const { t } = useLanguage();

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(false);

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
                {t("header.adminLogin")}
            </h1>

            <Card>
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
