import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import StatusMessage from "@/components/ui/StatusMessage";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";

describe("StatusMessage", () => {
    it("renders an empty state without alert role", () => {
        render(
            <LanguageProvider>
                <StatusMessage message="なし" />
            </LanguageProvider>
        );

        expect(screen.getByText("なし")).toBeInTheDocument();
        expect(screen.queryByRole("alert")).not.toBeInTheDocument();
        expect(screen.queryByRole("button")).not.toBeInTheDocument();
    });

    it("renders errors as alerts with a working retry button", async () => {
        const onRetry = vi.fn();
        render(
            <LanguageProvider>
                <StatusMessage variant="error" message="失敗" onRetry={onRetry} />
            </LanguageProvider>
        );

        expect(screen.getByRole("alert")).toHaveTextContent("失敗");
        await userEvent.click(screen.getByRole("button", { name: "再読み込み" }));
        expect(onRetry).toHaveBeenCalledOnce();
    });
});
