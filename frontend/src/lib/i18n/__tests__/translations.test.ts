import { describe, expect, it } from "vitest";
import { translations } from "@/lib/i18n/translations";

const PLACEHOLDER = /\{(\w+)\}/g;

function placeholders(template: string): string[] {
    return [...template.matchAll(PLACEHOLDER)].map((m) => m[1]).sort();
}

describe("translations", () => {
    it("has the same keys in every language", () => {
        expect(Object.keys(translations.en).sort()).toEqual(
            Object.keys(translations.ja).sort()
        );
    });

    it("has no empty strings", () => {
        for (const [lang, table] of Object.entries(translations)) {
            for (const [key, value] of Object.entries(table)) {
                expect(value.trim(), `${lang}.${key}`).not.toBe("");
            }
        }
    });

    it("uses identical placeholders in both languages", () => {
        for (const key of Object.keys(translations.ja) as (keyof typeof translations.ja)[]) {
            expect(placeholders(translations.en[key]), key).toEqual(
                placeholders(translations.ja[key])
            );
        }
    });
});
