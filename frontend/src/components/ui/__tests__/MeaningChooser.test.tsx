import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@/lib/api")>();
    return { ...actual, searchConcepts: vi.fn() };
});

import * as api from "@/lib/api";
import MeaningChooser from "@/components/ui/MeaningChooser";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";
import { ConceptSearchItem } from "@/types/concept";

const mocked = vi.mocked(api);

const wave: ConceptSearchItem = {
    id: 1,
    label: "位相",
    gloss: "波の位相",
    matched_term: "phase",
    question_count: 12,
};
const matter: ConceptSearchItem = {
    id: 2,
    label: "相",
    gloss: "物質の状態",
    matched_term: "phase",
    question_count: 4,
};

beforeEach(() => {
    mocked.searchConcepts.mockReset();
});

describe("MeaningChooser", () => {
    it("asks which meaning when a word names several senses", async () => {
        mocked.searchConcepts.mockResolvedValue([wave, matter]);
        const onSelect = vi.fn();
        render(
            <LanguageProvider>
                <MeaningChooser word="Phase" onSelect={onSelect} />
            </LanguageProvider>
        );

        await userEvent.click(await screen.findByText("位相 — 波の位相 (12)"));

        expect(onSelect).toHaveBeenCalledWith(wave);
    });

    it("stays hidden when the word has one meaning", async () => {
        mocked.searchConcepts.mockResolvedValue([
            wave,
            { ...matter, matched_term: "phase shift" },
        ]);
        render(
            <LanguageProvider>
                <MeaningChooser word="phase" onSelect={vi.fn()} />
            </LanguageProvider>
        );

        await waitFor(() => expect(mocked.searchConcepts).toHaveBeenCalled());
        expect(screen.queryByText(/複数の意味/)).not.toBeInTheDocument();
    });
});
