/**
 * `items`を`limit`件まで同時実行しながら`worker`を適用するヘルパー。
 * 大量のitemsを一括で全て並列実行してAPI/外部サービスへ負荷をかけすぎないようにする。
 */
export async function runWithConcurrencyLimit<T>(
    items: T[],
    limit: number,
    worker: (item: T) => Promise<void>
): Promise<void> {
    let index = 0;

    async function runNext(): Promise<void> {
        const current = index;
        index += 1;

        if (current >= items.length) {
            return;
        }

        await worker(items[current]);
        return runNext();
    }

    await Promise.all(
        Array.from({ length: Math.min(limit, items.length) }, runNext)
    );
}
