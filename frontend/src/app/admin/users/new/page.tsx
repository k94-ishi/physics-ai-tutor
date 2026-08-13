"use client";

import { SyntheticEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { createUser } from "@/lib/api";
import { UserRole } from "@/types/auth";
import Card from "@/components/ui/Card";
import TextField from "@/components/ui/TextField";
import SelectField from "@/components/ui/SelectField";
import Button from "@/components/ui/Button";
import { showToast } from "@/components/ui/Toast";

type FormErrors = {
    email?: string;
    password?: string;
};

export default function NewUserPage() {
    const router = useRouter();

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [role, setRole] = useState<UserRole>("user");
    const [loading, setLoading] = useState(false);
    const [errors, setErrors] = useState<FormErrors>({});

    const validate = (): FormErrors => {
        const nextErrors: FormErrors = {};

        if (!email.trim()) {
            nextErrors.email = "メールアドレスを入力してください。";
        }

        if (password.length < 8) {
            nextErrors.password = "8文字以上で入力してください。";
        }

        return nextErrors;
    };

    const handleSubmit = async (e: SyntheticEvent<HTMLFormElement>) => {
        e.preventDefault();

        const nextErrors = validate();
        setErrors(nextErrors);

        if (Object.keys(nextErrors).length > 0) {
            return;
        }

        setLoading(true);
        try {
            await createUser({ email, password, role });

            showToast("ユーザーを作成しました。");
            router.push("/admin/users");
        } catch (error) {
            console.error(error);
            showToast("ユーザーの作成に失敗しました。", "error");
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="flex flex-col gap-6">
            <h1 className="text-2xl font-bold text-gray-900">
                ユーザー作成
            </h1>

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
                        error={errors.email}
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                    />

                    <TextField
                        id="password"
                        label="パスワード"
                        type="password"
                        required
                        error={errors.password}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        autoComplete="new-password"
                    />

                    <SelectField
                        id="role"
                        label="権限"
                        value={role}
                        onChange={(e) => setRole(e.target.value as UserRole)}
                        options={[
                            { value: "user", label: "一般ユーザー" },
                            { value: "admin", label: "管理者" },
                        ]}
                    />

                    <Button
                        type="submit"
                        disabled={loading}
                        className="self-start"
                    >
                        {loading ? "作成中..." : "作成"}
                    </Button>
                </form>
            </Card>
        </main>
    );
}
