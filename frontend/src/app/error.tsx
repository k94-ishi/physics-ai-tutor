"use client";

import { useEffect } from "react";
import Button from "@/components/ui/Button";

export default function Error({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        console.error(error);
    }, [error]);

    return (
        <main className="flex flex-col items-start gap-4">
            <h1 className="text-xl font-bold text-gray-900">
                エラーが発生しました
            </h1>

            <p className="text-sm text-gray-600">
                しばらくしてから再度お試しください。
            </p>

            <Button onClick={() => reset()}>再試行</Button>
        </main>
    );
}
