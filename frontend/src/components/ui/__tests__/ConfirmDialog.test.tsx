import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";

function renderDialog(props: Partial<React.ComponentProps<typeof ConfirmDialog>> = {}) {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(
        <LanguageProvider>
            <ConfirmDialog
                open
                title="本当に削除しますか？"
                onConfirm={onConfirm}
                onCancel={onCancel}
                {...props}
            />
        </LanguageProvider>
    );
    return { onConfirm, onCancel };
}

describe("ConfirmDialog", () => {
    it("renders nothing when closed", () => {
        renderDialog({ open: false });

        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("renders an accessible dialog with default labels", () => {
        renderDialog({ description: "元に戻せません" });

        const dialog = screen.getByRole("dialog");
        expect(dialog).toHaveAttribute("aria-modal", "true");
        expect(dialog).toHaveAccessibleName("本当に削除しますか？");
        expect(screen.getByText("元に戻せません")).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "削除" })).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "キャンセル" })).toBeInTheDocument();
    });

    it("fires confirm and cancel callbacks", async () => {
        const { onConfirm, onCancel } = renderDialog({ confirmLabel: "承認" });

        await userEvent.click(screen.getByRole("button", { name: "承認" }));
        await userEvent.click(screen.getByRole("button", { name: "キャンセル" }));

        expect(onConfirm).toHaveBeenCalledOnce();
        expect(onCancel).toHaveBeenCalledOnce();
    });

    it("closes on Escape", async () => {
        const { onCancel } = renderDialog();

        await userEvent.keyboard("{Escape}");

        expect(onCancel).toHaveBeenCalledOnce();
    });

    it("disables both buttons while confirming", () => {
        renderDialog({ confirming: true });

        expect(screen.getByRole("button", { name: "処理中..." })).toBeDisabled();
        expect(screen.getByRole("button", { name: "キャンセル" })).toBeDisabled();
    });
});
