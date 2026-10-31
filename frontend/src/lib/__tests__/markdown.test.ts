import { describe, expect, it } from "vitest";
import { normalizeMathDelimiters } from "@/lib/markdown";

describe("normalizeMathDelimiters", () => {
    it("converts inline \\( \\) delimiters to single dollars", () => {
        expect(normalizeMathDelimiters("速度は \\( v = at \\) です")).toBe(
            "速度は $v = at$ です"
        );
    });

    it("converts block \\[ \\] delimiters to double dollars", () => {
        expect(normalizeMathDelimiters("式:\n\\[ F = ma \\]\n終わり")).toBe(
            "式:\n$$F = ma$$\n終わり"
        );
    });

    it("handles double-escaped delimiters from JSON payloads", () => {
        expect(normalizeMathDelimiters("\\\\( x \\\\)")).toBe("$x$");
    });

    it("leaves existing dollar math and plain text untouched", () => {
        const input = "$E = mc^2$ と $$a^2 + b^2 = c^2$$ はそのまま";
        expect(normalizeMathDelimiters(input)).toBe(input);
    });

    it("does not treat inline delimiters spanning lines as math", () => {
        const input = "\\( a\nb \\)";
        expect(normalizeMathDelimiters(input)).toBe(input);
    });
});
