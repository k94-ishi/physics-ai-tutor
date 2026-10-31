import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import QuestionIdBadge from "@/components/ui/QuestionIdBadge";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";

describe("QuestionIdBadge", () => {
    it("shows the id in the form issues and eval cases quote it", () => {
        render(
            <LanguageProvider>
                <QuestionIdBadge id={54} />
            </LanguageProvider>
        );

        expect(screen.getByRole("button")).toHaveTextContent("#54");
    });

    it("copies the bare number, not the # prefix", async () => {
        const writeText = vi.fn().mockResolvedValue(undefined);
        vi.stubGlobal("navigator", { clipboard: { writeText } });

        render(
            <LanguageProvider>
                <QuestionIdBadge id={848} />
            </LanguageProvider>
        );
        await userEvent.click(screen.getByRole("button"));

        expect(writeText).toHaveBeenCalledWith("848");
        vi.unstubAllGlobals();
    });

    it("stays quiet when the clipboard is unavailable", async () => {
        const writeText = vi.fn().mockRejectedValue(new Error("denied"));
        vi.stubGlobal("navigator", { clipboard: { writeText } });

        render(
            <LanguageProvider>
                <QuestionIdBadge id={1} />
            </LanguageProvider>
        );

        await expect(
            userEvent.click(screen.getByRole("button"))
        ).resolves.not.toThrow();
        vi.unstubAllGlobals();
    });
});
