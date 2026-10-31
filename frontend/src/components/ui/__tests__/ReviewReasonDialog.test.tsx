import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ReviewReasonDialog from "@/components/ui/ReviewReasonDialog";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";

const onConfirm = vi.fn();
const onCancel = vi.fn();

function renderDialog() {
    return render(
        <LanguageProvider>
            <ReviewReasonDialog
                open
                title="却下の理由"
                onConfirm={onConfirm}
                onCancel={onCancel}
            />
        </LanguageProvider>
    );
}

beforeEach(() => {
    onConfirm.mockReset();
    onCancel.mockReset();
});

describe("ReviewReasonDialog", () => {
    it("confirms with the selected reason and trimmed comment", async () => {
        const user = userEvent.setup();
        renderDialog();

        await user.selectOptions(screen.getByLabelText("理由"), "TOO_ADVANCED");
        await user.type(screen.getByRole("textbox"), " 微積分を使用 ");
        await user.click(screen.getByRole("button", { name: "確定" }));

        expect(onConfirm).toHaveBeenCalledWith("TOO_ADVANCED", "微積分を使用");
    });

    it("blocks OTHER without a comment, mirroring the API rule", async () => {
        const user = userEvent.setup();
        renderDialog();

        await user.selectOptions(screen.getByLabelText("理由"), "OTHER");
        await user.click(screen.getByRole("button", { name: "確定" }));

        expect(onConfirm).not.toHaveBeenCalled();

        await user.type(screen.getByRole("textbox"), "別の理由");
        await user.click(screen.getByRole("button", { name: "確定" }));

        expect(onConfirm).toHaveBeenCalledWith("OTHER", "別の理由");
    });
});
