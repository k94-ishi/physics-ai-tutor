"use client";

export default function Error({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    return (
        <main>
            <h1>エラーが発生しました</h1>
            <p>{error.message}</p>
            <button onClick={() => reset()}>再試行</button>
        </main>
    );
}
