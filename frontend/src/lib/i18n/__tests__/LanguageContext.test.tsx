import { act, render, renderHook, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { LanguageProvider, useLanguage } from "@/lib/i18n/LanguageContext";
import T from "@/components/ui/T";

function wrapper({ children }: { children: React.ReactNode }) {
    return <LanguageProvider>{children}</LanguageProvider>;
}

beforeEach(() => {
    localStorage.clear();
    document.documentElement.lang = "";
});

describe("LanguageProvider", () => {
    it("defaults to Japanese and translates keys", () => {
        const { result } = renderHook(() => useLanguage(), { wrapper });

        expect(result.current.language).toBe("ja");
        expect(result.current.t("common.delete")).toBe("削除");
    });

    it("interpolates placeholders and leaves unknown ones intact", () => {
        const { result } = renderHook(() => useLanguage(), { wrapper });

        expect(result.current.t("common.selectedCount", { count: 3 })).toBe(
            "3件選択中"
        );
        expect(result.current.t("common.selectedCount")).toBe("{count}件選択中");
    });

    it("switches language, persists it, and updates <html lang>", () => {
        const { result } = renderHook(() => useLanguage(), { wrapper });

        act(() => result.current.setLanguage("en"));

        expect(result.current.language).toBe("en");
        expect(result.current.t("common.delete")).toBe("Delete");
        expect(localStorage.getItem("language")).toBe("en");
        expect(document.documentElement.lang).toBe("en");
    });

    it("restores the stored language on mount", () => {
        localStorage.setItem("language", "en");

        const { result } = renderHook(() => useLanguage(), { wrapper });

        expect(result.current.language).toBe("en");
    });

    it("ignores invalid stored values", () => {
        localStorage.setItem("language", "fr");

        const { result } = renderHook(() => useLanguage(), { wrapper });

        expect(result.current.language).toBe("ja");
    });

    it("throws when used outside the provider", () => {
        expect(() => renderHook(() => useLanguage())).toThrow(
            "useLanguage must be used within a LanguageProvider"
        );
    });
});

describe("<T>", () => {
    it("renders the translated string as a leaf", () => {
        render(<T k="common.selectedCount" params={{ count: 2 }} />, { wrapper });

        expect(screen.getByText("2件選択中")).toBeInTheDocument();
    });
});
