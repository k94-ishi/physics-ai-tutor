"use client";

import { SyntheticEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/AuthContext";
import Card from "@/components/ui/Card";
import TextField from "@/components/ui/TextField";
import Button from "@/components/ui/Button";
import StatusMessage from "@/components/ui/StatusMessage";

export default function LoginPage() {
    const router = useRouter();
    const { login } = useAuth();

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
            router.push("/admin/questions");
        } catch (err) {
            console.error(err);
            setError(true);
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="mx-auto flex max-w-sm flex-col gap-6">
            <h1 className="text-2xl font-bold text-gray-900">ログイン</h1>

            <Card>
                <form
                    onSubmit={handleSubmit}
                    noValidate
                    className="flex flex-col gap-5"
                >
                    <TextField
                        id="email"
                        label="メールアドレス"
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        autoComplete="username"
                    />

                    <TextField
                        id="password"
                        label="パスワード"
                        type="password"
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        autoComplete="current-password"
                    />

                    {error && (
                        <StatusMessage
                            variant="error"
                            message="メールアドレスまたはパスワードが正しくありません。"
                        />
                    )}

                    <Button type="submit" disabled={loading} className="self-start">
                        {loading ? "ログイン中..." : "ログイン"}
                    </Button>
                </form>
            </Card>
        </main>
    );
}
