/** Run `worker` over `items` with at most `limit` calls at a time. */
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
