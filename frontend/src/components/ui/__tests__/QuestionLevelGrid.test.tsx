import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Question } from "@/types/question";
import QuestionLevelGrid, {
    gridBounds,
    hasCoordinates,
} from "@/components/ui/QuestionLevelGrid";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";

function question(
    id: number,
    physics: number | null,
    math: number | null,
    text = `質問${id}`
): Question {
    return {
        id,
        question: text,
        answer: "回答",
        language: "ja",
        provenance: "ORIGINAL",
        original_language: "ja",
        available_languages: ["ja"],
        texts: {},
        status: "APPROVED",
        source: "MANUAL",
        concepts: [],
        retrieved_questions: [],
        physics_level: physics,
        math_level: math,
    };
}

function renderGrid(
    current: Question,
    items: Question[],
    onPreview = vi.fn()
) {
    render(
        <LanguageProvider>
            <QuestionLevelGrid
                current={current}
                items={items}
                onPreview={onPreview}
            />
        </LanguageProvider>
    );
    return onPreview;
}

describe("helpers", () => {
    it("requires both coordinates", () => {
        expect(hasCoordinates(question(1, 2, 0))).toBe(true);
        expect(hasCoordinates(question(1, 2, null))).toBe(false);
        expect(hasCoordinates(question(1, null, 0))).toBe(false);
    });

    it("bounds cover the current question and every item", () => {
        expect(
            gridBounds(question(1, 2, 3), [question(2, 0, 1), question(3, 3, 3)])
        ).toEqual({ minP: 0, maxP: 3, minM: 1, maxM: 3 });
    });
});

describe("QuestionLevelGrid", () => {
    it("marks the current question's cell and places a lower item", () => {
        renderGrid(question(1, 2, 3), [question(2, 1, 1, "ベクトルってなに？")]);

        expect(screen.getByText("今ここ")).toBeInTheDocument();
        expect(screen.getByText("ベクトルってなに？")).toBeInTheDocument();
        // Rows run from the highest math level down to the lowest present.
        const rowLabels = screen
            .getAllByRole("rowheader")
            .map((cell) => cell.textContent);
        expect(rowLabels).toEqual(["3", "2", "1"]);
    });

    it("previews an item on click and skips unrated items", () => {
        const target = question(2, 1, 1, "ベクトルってなに？");
        const onPreview = renderGrid(question(1, 2, 3), [
            target,
            question(3, null, null, "未評価の質問"),
        ]);

        expect(screen.queryByText("未評価の質問")).not.toBeInTheDocument();

        fireEvent.click(screen.getByText("ベクトルってなに？"));
        expect(onPreview).toHaveBeenCalledWith(target);
    });

    it("renders nothing when the current question or all items lack levels", () => {
        const { container } = render(
            <LanguageProvider>
                <QuestionLevelGrid
                    current={question(1, null, null)}
                    items={[question(2, 1, 1)]}
                    onPreview={vi.fn()}
                />
                <QuestionLevelGrid
                    current={question(3, 2, 2)}
                    items={[question(4, null, 1)]}
                    onPreview={vi.fn()}
                />
            </LanguageProvider>
        );

        expect(container).toBeEmptyDOMElement();
    });
});
