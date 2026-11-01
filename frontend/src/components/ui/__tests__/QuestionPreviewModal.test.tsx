import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import QuestionPreviewModal from "@/components/ui/QuestionPreviewModal";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";
import { Question } from "@/types/question";

const QUESTION = {
    id: 42,
    question: "終端速度とは何ですか？",
    answer: "空気抵抗と重力がつり合ったときの一定の速さです。",
    concepts: ["終端速度", "空気抵抗"],
} as unknown as Question;

function renderModal(question: Question | null, onClose = vi.fn()) {
    render(
        <LanguageProvider>
            <QuestionPreviewModal question={question} onClose={onClose} />
        </LanguageProvider>
    );
    return onClose;
}

describe("QuestionPreviewModal", () => {
    it("renders nothing when no question is selected", () => {
        renderModal(null);

        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("shows the full answer, its concepts, and a way to the full page", () => {
        renderModal(QUESTION);

        const dialog = screen.getByRole("dialog");
        expect(dialog).toHaveAttribute("aria-modal", "true");
        expect(screen.getByText("終端速度とは何ですか？")).toBeInTheDocument();
        expect(
            screen.getByText(/空気抵抗と重力がつり合ったとき/)
        ).toBeInTheDocument();
        expect(
            screen.getByRole("link", { name: "この質問のページを開く" })
        ).toHaveAttribute("href", "/questions/42");
        // Concepts stay reachable from inside the preview.
        expect(screen.getByRole("link", { name: "終端速度" })).toBeInTheDocument();
    });

    it("closes on the button, on Escape, and on the backdrop", async () => {
        const user = userEvent.setup();

        const onClose = renderModal(QUESTION);
        await user.click(screen.getByRole("button", { name: "閉じる" }));
        expect(onClose).toHaveBeenCalledTimes(1);

        await user.keyboard("{Escape}");
        expect(onClose).toHaveBeenCalledTimes(2);

        await user.click(screen.getByRole("dialog"));
        expect(onClose).toHaveBeenCalledTimes(3);
    });

    it("does not close when the content itself is clicked", async () => {
        const user = userEvent.setup();
        const onClose = renderModal(QUESTION);

        await user.click(screen.getByText("終端速度とは何ですか？"));

        expect(onClose).not.toHaveBeenCalled();
    });

    it("restores page scrolling when it unmounts", () => {
        const { unmount } = render(
            <LanguageProvider>
                <QuestionPreviewModal question={QUESTION} onClose={vi.fn()} />
            </LanguageProvider>
        );

        expect(document.body.style.overflow).toBe("hidden");
        unmount();
        expect(document.body.style.overflow).not.toBe("hidden");
    });
});
