import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const replace = vi.fn();
let currentSearch = "";

vi.mock("next/navigation", () => ({
    useRouter: () => ({ replace }),
    usePathname: () => "/questions",
    useSearchParams: () => new URLSearchParams(currentSearch),
}));

import { useQueryState } from "@/lib/hooks/useQueryState";

const DEFAULTS = { page: "1", size: "30", keyword: "" };

beforeEach(() => {
    replace.mockReset();
    currentSearch = "";
});

describe("useQueryState", () => {
    it("returns defaults when the URL has no params", () => {
        const { result } = renderHook(() => useQueryState(DEFAULTS));

        expect(result.current[0]).toEqual(DEFAULTS);
    });

    it("reads values from the URL over defaults", () => {
        currentSearch = "page=3&keyword=速度";

        const { result } = renderHook(() => useQueryState(DEFAULTS));

        expect(result.current[0]).toEqual({ page: "3", size: "30", keyword: "速度" });
    });

    it("writes non-default values to the URL without scrolling", () => {
        const { result } = renderHook(() => useQueryState(DEFAULTS));

        act(() => result.current[1]({ page: "2", keyword: "加速度" }));

        expect(replace).toHaveBeenCalledWith(
            "/questions?page=2&keyword=%E5%8A%A0%E9%80%9F%E5%BA%A6",
            { scroll: false }
        );
    });

    it("drops params that equal their default", () => {
        currentSearch = "page=4&size=60";

        const { result } = renderHook(() => useQueryState(DEFAULTS));

        act(() => result.current[1]({ page: "1" }));

        expect(replace).toHaveBeenCalledWith("/questions?size=60", { scroll: false });
    });

    it("produces a bare pathname when everything is default", () => {
        currentSearch = "page=2";

        const { result } = renderHook(() => useQueryState(DEFAULTS));

        act(() => result.current[1]({ page: "1" }));

        expect(replace).toHaveBeenCalledWith("/questions", { scroll: false });
    });
});
