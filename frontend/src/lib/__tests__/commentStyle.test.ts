import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

// Comments are English (AGENTS.md coding style, [65]); quoted Japanese is data.
const SRC = join(__dirname, "..", "..");
const JAPANESE = /[぀-ヿ㐀-鿿！-｠]/g;
const QUOTED = /`[^`]*`|"[^"]*"|'[^']*'|「[^」]*」/g;
// Translation tables hold Japanese UI text by design; it is data, not comment.
const DATA_FILES = [join("lib", "i18n", "translations")];

export function isJapaneseProse(text: string): boolean {
    const letters = text.replace(QUOTED, "").replace(/\s/g, "");
    if (letters.length === 0) return false;
    return (letters.match(JAPANESE)?.length ?? 0) / letters.length >= 0.2;
}

function sourceFiles(dir: string): string[] {
    return readdirSync(dir).flatMap((name) => {
        const path = join(dir, name);
        if (statSync(path).isDirectory()) return sourceFiles(path);
        return /\.(ts|tsx)$/.test(name) ? [path] : [];
    });
}

function comments(source: string): { line: number; text: string }[] {
    const found: { line: number; text: string }[] = [];
    // Line comments not inside a string on that line, and block comments.
    const pattern = /(^|[^:"'`])\/\/([^\n]*)|\/\*([\s\S]*?)\*\//g;
    for (const match of source.matchAll(pattern)) {
        const line = source.slice(0, match.index).split("\n").length;
        found.push({ line, text: match[2] ?? match[3] ?? "" });
    }
    return found;
}

describe("comment language ([65])", () => {
    it("no comment in src is Japanese prose", () => {
        const offenders = sourceFiles(SRC)
            .filter(
                (path) =>
                    !DATA_FILES.some((d) => relative(SRC, path).startsWith(d)),
            )
            .flatMap((path) =>
                comments(readFileSync(path, "utf8"))
                    .filter((c) => isJapaneseProse(c.text))
                    .map((c) => `${relative(SRC, path)}:${c.line}`),
            );

        expect(offenders).toEqual([]);
    });

    it("tells prose from quoted data", () => {
        expect(isJapaneseProse("概念抽出は質問ごとに並列で実行する")).toBe(
            true,
        );
        expect(
            isJapaneseProse(
                "Wait for the language, or the list loads in ja first.",
            ),
        ).toBe(false);
        expect(
            isJapaneseProse(
                "CommonMark reads the ** between 」 and と as an opener.",
            ),
        ).toBe(false);
    });
});
