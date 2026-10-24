import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// Unmount rendered trees between tests so state never leaks across cases.
afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

process.env.NEXT_PUBLIC_API_URL = "http://api.test";

// jsdom does not ship a usable Web Storage implementation; provide one.
class MemoryStorage implements Storage {
    private store = new Map<string, string>();

    get length(): number {
        return this.store.size;
    }

    clear(): void {
        this.store.clear();
    }

    getItem(key: string): string | null {
        return this.store.get(key) ?? null;
    }

    key(index: number): string | null {
        return [...this.store.keys()][index] ?? null;
    }

    removeItem(key: string): void {
        this.store.delete(key);
    }

    setItem(key: string, value: string): void {
        this.store.set(key, String(value));
    }
}

if (typeof globalThis.localStorage?.clear !== "function") {
    Object.defineProperty(globalThis, "localStorage", {
        value: new MemoryStorage(),
        configurable: true,
    });
}
