import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import AdminQuestionCard from "@/components/admin/AdminQuestionCard";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";
import { Question } from "@/types/question";

const QUESTION: Question = {
    id: 54,
    question: "速度ってなに？",
    answer: "向きを含む速さ。",
    language: "ja",
    provenance: "ORIGINAL",
    original_language: "ja",
    available_languages: ["ja"],
    texts: {},
    status: "UNREVIEWED",
    source: "AI_GENERATED",
    concepts: ["ベクトル"],
    physics_level: 1,
    math_level: 1,
    retrieved_questions: [],
    generation: null,
    ai_review: null,
};

function renderCard(
    overrides: Partial<Parameters<typeof AdminQuestionCard>[0]> = {},
) {
    const handlers = {
        onToggleSelected: vi.fn(),
        onFilterConcept: vi.fn(),
        onApprove: vi.fn(),
        onReject: vi.fn(),
        onAiReview: vi.fn(),
        onExtract: vi.fn(),
        onDelete: vi.fn(),
    };
    render(
        <LanguageProvider>
            <AdminQuestionCard
                question={QUESTION}
                isSelected={false}
                extraction={undefined}
                review={undefined}
                aiReviewing={false}
                aiBusy={false}
                activeConcept=""
                {...handlers}
                {...overrides}
            />
        </LanguageProvider>,
    );
    return handlers;
}

describe("AdminQuestionCard ([63])", () => {
    it("each action button calls only its own callback", async () => {
        const user = userEvent.setup();
        const handlers = renderCard();

        await user.click(screen.getByRole("button", { name: "承認" }));
        await user.click(screen.getByRole("button", { name: "却下" }));
        await user.click(screen.getByRole("button", { name: "タグ抽出" }));
        await user.click(screen.getByRole("button", { name: "削除" }));

        expect(handlers.onApprove).toHaveBeenCalledTimes(1);
        expect(handlers.onReject).toHaveBeenCalledTimes(1);
        expect(handlers.onExtract).toHaveBeenCalledTimes(1);
        expect(handlers.onDelete).toHaveBeenCalledTimes(1);
        // Action buttons stop propagation: they never toggle selection.
        expect(handlers.onToggleSelected).not.toHaveBeenCalled();
    });

    it("a tag filters the queue (and, as before [63], also toggles selection)", async () => {
        const user = userEvent.setup();
        const handlers = renderCard();

        await user.click(screen.getByRole("button", { name: "ベクトル" }));

        expect(handlers.onFilterConcept).toHaveBeenCalledWith("ベクトル");
        // Pre-existing quirk kept by the refactor; the filter change clears
        // the selection anyway. Tracked in [63]'s log.
        expect(handlers.onToggleSelected).toHaveBeenCalledTimes(1);
    });

    it("clicking the card or its checkbox toggles selection once", async () => {
        const user = userEvent.setup();
        const handlers = renderCard();

        await user.click(screen.getByText("向きを含む速さ。"));
        await user.click(screen.getByRole("checkbox"));

        expect(handlers.onToggleSelected).toHaveBeenCalledTimes(2);
    });

    it("blocks AI review while a run is busy and hides approve once approved", () => {
        renderCard({
            aiBusy: true,
            question: { ...QUESTION, status: "APPROVED" },
        });

        expect(
            screen.queryByRole("button", { name: "承認" }),
        ).not.toBeInTheDocument();
        const aiButtons = screen
            .getAllByRole("button")
            .filter((b) => b.textContent?.includes("AI"));
        expect(aiButtons.every((b) => (b as HTMLButtonElement).disabled)).toBe(
            true,
        );
    });
});
