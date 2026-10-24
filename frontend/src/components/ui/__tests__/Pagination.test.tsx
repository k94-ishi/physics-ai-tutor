import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Pagination from "@/components/ui/Pagination";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";

function renderPagination(props: Partial<React.ComponentProps<typeof Pagination>> = {}) {
    const onPageChange = vi.fn();
    const onSizeChange = vi.fn();
    render(
        <LanguageProvider>
            <Pagination
                page={1}
                size={30}
                total={100}
                onPageChange={onPageChange}
                onSizeChange={onSizeChange}
                {...props}
            />
        </LanguageProvider>
    );
    return { onPageChange, onSizeChange };
}

describe("Pagination", () => {
    it("shows the current range and marks the active page", () => {
        renderPagination({ page: 2 });

        expect(screen.getByText(/31/)).toBeInTheDocument();
        expect(screen.getByRole("button", { current: "page" })).toHaveTextContent("2");
    });

    it("disables previous on the first page and next on the last", () => {
        renderPagination({ page: 4, total: 100, size: 30 });

        expect(screen.getByRole("button", { name: "前のページ" })).toBeEnabled();
        expect(screen.getByRole("button", { name: "次のページ" })).toBeDisabled();
    });

    it("collapses distant pages into an ellipsis", () => {
        renderPagination({ page: 1, total: 3000, size: 30 });

        expect(screen.getByText("…")).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "100" })).toBeInTheDocument();
        expect(screen.queryByRole("button", { name: "50" })).not.toBeInTheDocument();
    });

    it("calls onPageChange when a page button is clicked", async () => {
        const { onPageChange } = renderPagination();

        await userEvent.click(screen.getByRole("button", { name: "3" }));

        expect(onPageChange).toHaveBeenCalledWith(3);
    });

    it("jumps to the typed page on submit and clears the input", async () => {
        const { onPageChange } = renderPagination({ total: 100, size: 30 });
        const input = screen.getByRole("spinbutton");

        await userEvent.type(input, "3{enter}");

        expect(onPageChange).toHaveBeenCalledWith(3);
        expect(input).toHaveValue(null);
    });

    it("bounds the jump input to the last page", () => {
        renderPagination({ total: 100, size: 30 });

        expect(screen.getByRole("spinbutton")).toHaveAttribute("max", "4");
    });

    it("ignores an empty jump submission", async () => {
        const { onPageChange } = renderPagination();

        await userEvent.click(screen.getByRole("button", { name: "移動" }));

        expect(onPageChange).not.toHaveBeenCalled();
    });

    it("calls onSizeChange with a number", async () => {
        const { onSizeChange } = renderPagination();

        await userEvent.selectOptions(screen.getByRole("combobox"), "60");

        expect(onSizeChange).toHaveBeenCalledWith(60);
    });

    it("shows 0 range for an empty result set", () => {
        renderPagination({ total: 0 });

        expect(screen.getByText(/^0/)).toBeInTheDocument();
    });
});
