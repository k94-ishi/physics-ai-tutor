import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Question } from "@/types/question";

vi.mock("@/lib/api", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@/lib/api")>();
    return { ...actual, fetchQuestions: vi.fn(), updateQuestion: vi.fn() };
});

import * as api from "@/lib/api";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";
import AdminLevelsPage, { agreementByField, STORAGE_KEY } from "../page";

const mocked = vi.mocked(api);

function question(id: number, levels: (number | null)[]): Question {
    const [qp, qm, ap, am] = levels;
    return {
        id,
        question: `質問${id}`,
        answer: `回答${id}`,
        language: "ja",
        provenance: "ORIGINAL",
        original_language: "ja",
        available_languages: ["ja"],
        texts: {},
        status: "APPROVED",
        source: "MANUAL",
        concepts: ["速度"],
        question_physics_level: qp,
        question_math_level: qm,
        answer_physics_level: ap,
        answer_math_level: am,
        retrieved_questions: [],
    };
}

const ROWS = [question(1, [1, 0, 1, 1]), question(2, [3, 3, 3, 3]), question(3, [null, null, null, null])];

beforeEach(() => {
    window.localStorage.clear();
    mocked.fetchQuestions.mockReset().mockResolvedValue({
        items: ROWS,
        total: ROWS.length,
        page: 1,
        size: 120,
    });
    mocked.updateQuestion.mockReset();
});

describe("agreementByField", () => {
    it("counts exact and within-one matches only where both ratings exist", () => {
        const stats = agreementByField(ROWS, {
            1: { question_physics_level: 1, question_math_level: 1 },
            2: { question_physics_level: 1 },
            3: { question_physics_level: 2 },
        });

        expect(stats.question_physics_level).toEqual({ n: 2, exact: 1, within1: 1, meanOffset: 1 });
        expect(stats.question_math_level).toEqual({ n: 1, exact: 0, within1: 1, meanOffset: -1 });
        expect(stats.answer_math_level.n).toBe(0);
    });
});

describe("AdminLevelsPage", () => {
    it("lists approved questions with the LLM levels and keeps my rating in the browser", async () => {
        render(
            <LanguageProvider>
                <AdminLevelsPage />
            </LanguageProvider>
        );

        expect(await screen.findByText("質問1")).toBeInTheDocument();
        expect(mocked.fetchQuestions).toHaveBeenCalledWith(
            expect.objectContaining({ status: "APPROVED", size: 120 })
        );
        expect(screen.getByText("まだ自分の評価がありません。")).toBeInTheDocument();

        fireEvent.change(screen.getByLabelText("自分 質問 物理 #1"), { target: { value: "2" } });

        expect(JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "{}")).toEqual({
            1: { question_physics_level: 2 },
        });
        expect(screen.getByText("一致率(自分の評価があるものだけ)")).toBeInTheDocument();
        expect(screen.getByText("±1以内")).toBeInTheDocument();
    });

    it("saves my rating as a teacher correction through the update endpoint", async () => {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ 2: { answer_math_level: 4 } }));
        mocked.updateQuestion.mockResolvedValue(question(2, [3, 3, 3, 4]));

        render(
            <LanguageProvider>
                <AdminLevelsPage />
            </LanguageProvider>
        );

        await screen.findByText("質問2");
        const buttons = screen.getAllByRole("button", { name: "教員の修正として保存" });
        const enabled = buttons.filter((b) => !(b as HTMLButtonElement).disabled);
        expect(enabled).toHaveLength(1);

        fireEvent.click(enabled[0]);

        expect(mocked.updateQuestion).toHaveBeenCalledWith({ id: 2, answer_math_level: 4 });
    });
});
