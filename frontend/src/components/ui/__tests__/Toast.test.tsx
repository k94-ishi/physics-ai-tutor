import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import Toaster, { showToast } from "@/components/ui/Toast";
import { ASK_BAR_HEIGHT_VAR } from "@/components/StickyAskBar";

afterEach(() => {
    document.documentElement.style.removeProperty(ASK_BAR_HEIGHT_VAR);
});

describe("Toaster", () => {
    it("offsets itself by the sticky ask bar's height ([43])", () => {
        // The bar publishes its measured height; the toast must clear it
        // instead of hiding behind it.
        document.documentElement.style.setProperty(ASK_BAR_HEIGHT_VAR, "96px");
        render(<Toaster />);

        act(() => showToast("保存しました"));

        const toast = screen.getByRole("status");
        expect(toast.parentElement).toHaveStyle({
            bottom: "calc(1rem + var(--ask-bar-height, 0px))",
        });
    });

    it("renders nothing until a toast is shown", () => {
        const { container } = render(<Toaster />);

        expect(container).toBeEmptyDOMElement();
    });
});
