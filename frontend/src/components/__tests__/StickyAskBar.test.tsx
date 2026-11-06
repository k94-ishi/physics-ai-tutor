import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import StickyAskBar, { ASK_BAR_HEIGHT_VAR } from "@/components/StickyAskBar";

const BAR_HEIGHT = 96;

function mockMeasuredHeight(height: number) {
    const spy = vi
        .spyOn(HTMLElement.prototype, "getBoundingClientRect")
        .mockReturnValue({ height } as DOMRect);
    return spy;
}

afterEach(() => {
    vi.restoreAllMocks();
    document.documentElement.style.removeProperty(ASK_BAR_HEIGHT_VAR);
});

describe("StickyAskBar", () => {
    it("pins its content to the bottom of the viewport", () => {
        render(
            <StickyAskBar>
                <button type="button">質問する</button>
            </StickyAskBar>
        );

        const bar = screen.getByTestId("sticky-ask-bar");
        expect(bar.className).toContain("fixed");
        expect(bar.className).toContain("bottom-0");
        expect(screen.getByRole("button", { name: "質問する" })).toBeInTheDocument();
    });

    it("reserves the same height in the flow so content is never hidden", async () => {
        mockMeasuredHeight(BAR_HEIGHT);
        const { container } = render(
            <StickyAskBar>
                <p>入力欄</p>
            </StickyAskBar>
        );

        const spacer = container.querySelector('[aria-hidden="true"]');
        await waitFor(() =>
            expect(spacer).toHaveStyle({ height: `${BAR_HEIGHT}px` })
        );
    });

    it("publishes its height so toasts can sit above it", async () => {
        mockMeasuredHeight(BAR_HEIGHT);
        const { unmount } = render(
            <StickyAskBar>
                <p>入力欄</p>
            </StickyAskBar>
        );

        await waitFor(() =>
            expect(
                document.documentElement.style.getPropertyValue(ASK_BAR_HEIGHT_VAR)
            ).toBe(`${BAR_HEIGHT}px`)
        );

        // Pages without the bar must not keep a stale offset.
        unmount();
        expect(
            document.documentElement.style.getPropertyValue(ASK_BAR_HEIGHT_VAR)
        ).toBe("");
    });

    it("caps its height and scrolls instead of covering the page", () => {
        render(
            <StickyAskBar>
                <p>検索結果がたくさん</p>
            </StickyAskBar>
        );

        const scroller = screen.getByText("検索結果がたくさん").parentElement;
        expect(scroller).toHaveStyle({ maxHeight: "70svh" });
        expect(scroller?.className).toContain("overflow-y-auto");
    });
});
