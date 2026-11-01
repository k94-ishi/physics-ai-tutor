import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import MarkdownContent from "@/components/ui/MarkdownContent";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";

// Mermaid renders in a browser only; the diagram case just needs the branch.
vi.mock("@/components/ui/MermaidDiagram", () => ({
    default: ({ code }: { code: string }) => <pre data-testid="mermaid">{code}</pre>,
}));

function renderMarkdown(content: string) {
    const { container } = render(
        <LanguageProvider>
            <MarkdownContent content={content} />
        </LanguageProvider>
    );
    return container;
}

describe("MarkdownContent CJK emphasis", () => {
    it("closes bold that ends on fullwidth punctuation", () => {
        // CommonMark alone reads the second ** as an opener (it sits between
        // 」 and と), so the asterisks used to show up as text.
        const container = renderMarkdown(
            "物体が転倒するかどうかの判断は、**「重心の位置」**と**「支持面（接地している範囲）」**の関係で決まります。"
        );

        expect(container.textContent).not.toContain("**");
        const bolded = Array.from(container.querySelectorAll("strong")).map(
            (node) => node.textContent
        );
        expect(bolded).toEqual(["「重心の位置」", "「支持面（接地している範囲）」"]);
    });

    it("handles bold butted against other CJK punctuation", () => {
        const container = renderMarkdown(
            "**力のモーメント（回転させる効果）**のつり合い、**半減期。**という考え方。"
        );

        expect(container.textContent).not.toContain("**");
        expect(container.querySelectorAll("strong")).toHaveLength(2);
    });

    it("fixes a real approved answer without changing its text", () => {
        // From seed.json; 21 of 144 approved answers carry this shape.
        const container = renderMarkdown(
            "答えは**「方向ごとに独立して扱えるから」**です。"
        );

        expect(container.textContent).toBe(
            "答えは「方向ごとに独立して扱えるから」です。"
        );
        expect(container.querySelector("strong")?.textContent).toBe(
            "「方向ごとに独立して扱えるから」"
        );
    });

    it("leaves ordinary English emphasis alone", () => {
        const container = renderMarkdown("This is **important** text.");

        expect(container.querySelector("strong")?.textContent).toBe("important");
        expect(container.textContent).not.toContain("**");
    });

    it("still renders math, tables and diagrams", () => {
        const container = renderMarkdown(
            [
                "速度は $v = at$ です。",
                "",
                "| 記号 | 意味 |",
                "| --- | --- |",
                "| $a$ | 加速度 |",
                "",
                "```mermaid",
                "graph TD; A-->B;",
                "```",
            ].join("\n")
        );

        expect(container.querySelector(".katex")).toBeTruthy();
        expect(container.querySelector("table")).toBeTruthy();
        expect(screen.getByTestId("mermaid")).toHaveTextContent("graph TD; A-->B;");
    });
});
