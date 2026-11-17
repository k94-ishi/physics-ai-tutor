import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

const SRC = join(__dirname, "..", "..", "..");

function sourceFiles(dir: string): string[] {
    return readdirSync(dir).flatMap((name) => {
        const path = join(dir, name);
        if (statSync(path).isDirectory()) return sourceFiles(path);
        return /\.(ts|tsx)$/.test(name) ? [path] : [];
    });
}

describe("API import boundary ([64])", () => {
    it("code outside lib/api imports only @/lib/api, never a feature file", () => {
        // vi.mock("@/lib/api") would not reach a direct feature import.
        const offenders = sourceFiles(SRC)
            .filter((path) => !relative(SRC, path).startsWith(join("lib", "api")))
            .filter((path) => /from "@\/lib\/api\/[a-z]/.test(readFileSync(path, "utf8")))
            .map((path) => relative(SRC, path));

        expect(offenders).toEqual([]);
    });
});
