import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useLatestRequest } from "@/lib/hooks/useLatestRequest";

describe("useLatestRequest", () => {
    it("only the newest request stays current", () => {
        const { result } = renderHook(() => useLatestRequest());

        const first = result.current.begin();
        const second = result.current.begin();

        expect(first()).toBe(false);
        expect(second()).toBe(true);
    });

    it("cancel makes every started request stale", () => {
        const { result } = renderHook(() => useLatestRequest());
        const pending = result.current.begin();

        result.current.cancel();

        expect(pending()).toBe(false);
    });

    it("is the same object on every render", () => {
        const { result, rerender } = renderHook(() => useLatestRequest());
        const before = result.current;

        rerender();

        expect(result.current).toBe(before);
    });
});
