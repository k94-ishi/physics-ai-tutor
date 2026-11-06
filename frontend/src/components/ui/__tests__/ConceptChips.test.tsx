import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import ConceptChips, { VISIBLE_CONCEPTS } from "@/components/ui/ConceptChips";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";

function renderChips(concepts: string[]) {
    return render(
        <LanguageProvider>
            <ConceptChips concepts={concepts} />
        </LanguageProvider>
    );
}

describe("ConceptChips", () => {
    it("links each concept to the questions that share it", () => {
        renderChips(["微分方程式", "終端速度"]);

        expect(screen.getByRole("link", { name: "微分方程式" })).toHaveAttribute(
            "href",
            "/?concept=%E5%BE%AE%E5%88%86%E6%96%B9%E7%A8%8B%E5%BC%8F"
        );
        expect(screen.getByRole("link", { name: "終端速度" })).toBeInTheDocument();
    });

    it("renders nothing when the question has no concepts", () => {
        const { container } = renderChips([]);

        expect(container).toBeEmptyDOMElement();
    });

    it("caps the visible chips and reveals the rest on demand", async () => {
        // Answers routinely yield 8-15 concepts; all of them would push the
        // answer below the fold on a phone.
        const many = Array.from({ length: VISIBLE_CONCEPTS + 3 }, (_, i) =>
            `概念${String(i).padStart(2, "0")}`
        );
        const user = userEvent.setup();
        renderChips(many);

        expect(screen.getAllByRole("link")).toHaveLength(VISIBLE_CONCEPTS);

        await user.click(screen.getByRole("button", { name: "ほか3件" }));

        expect(screen.getAllByRole("link")).toHaveLength(many.length);
        expect(screen.queryByRole("button")).not.toBeInTheDocument();
    });

    it("shows the shortest concepts first while centrality is unavailable", () => {
        renderChips(["非常に長い概念の名前", "力", "加速度"]);

        const labels = screen.getAllByRole("link").map((node) => node.textContent);
        expect(labels).toEqual(["力", "加速度", "非常に長い概念の名前"]);
    });
});
