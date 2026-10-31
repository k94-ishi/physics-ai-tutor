import { describe, expect, it } from "vitest";
import { runWithConcurrencyLimit } from "@/lib/concurrency";

function deferred() {
    let resolve!: () => void;
    const promise = new Promise<void>((r) => {
        resolve = r;
    });
    return { promise, resolve };
}

describe("runWithConcurrencyLimit", () => {
    it("processes every item exactly once", async () => {
        const seen: number[] = [];

        await runWithConcurrencyLimit([1, 2, 3, 4, 5], 2, async (n) => {
            seen.push(n);
        });

        expect(seen.sort()).toEqual([1, 2, 3, 4, 5]);
    });

    it("never runs more than `limit` workers at once", async () => {
        const gates = [deferred(), deferred(), deferred(), deferred()];
        let active = 0;
        let peak = 0;

        const run = runWithConcurrencyLimit([0, 1, 2, 3], 2, async (i) => {
            active += 1;
            peak = Math.max(peak, active);
            await gates[i].promise;
            active -= 1;
        });

        // Let the first two start, then release them one by one.
        await Promise.resolve();
        expect(active).toBe(2);
        gates[0].resolve();
        gates[1].resolve();
        gates[2].resolve();
        gates[3].resolve();
        await run;

        expect(peak).toBe(2);
    });

    it("resolves immediately for an empty list", async () => {
        await expect(
            runWithConcurrencyLimit([], 3, async () => {
                throw new Error("should not be called");
            })
        ).resolves.toBeUndefined();
    });

    it("propagates worker errors", async () => {
        await expect(
            runWithConcurrencyLimit([1], 1, async () => {
                throw new Error("boom");
            })
        ).rejects.toThrow("boom");
    });
});
