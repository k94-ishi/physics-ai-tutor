import { act, render, renderHook, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import userEvent from "@testing-library/user-event";
import { LanguageProvider, useLanguage } from "@/lib/i18n/LanguageContext";
import T from "@/components/ui/T";

function wrapper({ children }: { children: React.ReactNode }) {
    return <LanguageProvider>{children}</LanguageProvider>;
}

beforeEach(() => {
    localStorage.clear();
    document.documentElement.lang = "";
    window.history.replaceState(null, "", "/");
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

describe("language in the URL ([50])", () => {
    function Probe() {
        const { language, setLanguage } = useLanguage();
        return (
            <div>
                <span data-testid="lang">{language}</span>
                <button type="button" onClick={() => setLanguage("en")}>
                    switch-en
                </button>
            </div>
        );
    }

    function renderProbe() {
        render(
            <LanguageProvider>
                <Probe />
            </LanguageProvider>
        );
    }

    it("URL wins over the stored preference, without overwriting it", async () => {
        localStorage.setItem("language", "ja");
        window.history.replaceState(null, "", "/?lang=en&similar=projectile");
        renderProbe();

        await waitFor(() =>
            expect(screen.getByTestId("lang")).toHaveTextContent("en")
        );
        // A shared link is ephemeral; the stored preference stays.
        expect(localStorage.getItem("language")).toBe("ja");
    });

    it("ignores garbage lang values", async () => {
        window.history.replaceState(null, "", "/?lang=fr");
        renderProbe();

        await waitFor(() =>
            expect(screen.getByTestId("lang")).toHaveTextContent("ja")
        );
    });

    it("an explicit switch updates a present lang param and keeps similar=", async () => {
        window.history.replaceState(null, "", "/?lang=ja&similar=斜方投射");
        const user = userEvent.setup();
        renderProbe();

        await user.click(screen.getByRole("button", { name: "switch-en" }));

        const params = new URLSearchParams(window.location.search);
        expect(params.get("lang")).toBe("en");
        // Owner's decision 2026-11-02: the query survives a language switch.
        expect(params.get("similar")).toBe("斜方投射");
        expect(localStorage.getItem("language")).toBe("en");
    });

    it("does not add lang to URLs that never had it", async () => {
        window.history.replaceState(null, "", "/?keyword=運動");
        const user = userEvent.setup();
        renderProbe();

        await user.click(screen.getByRole("button", { name: "switch-en" }));

        const params = new URLSearchParams(window.location.search);
        expect(params.get("lang")).toBeNull();
        expect(params.get("keyword")).toBe("運動");
    });

    it("back/forward to a lang-carrying URL re-applies that language", async () => {
        window.history.replaceState(null, "", "/?lang=en");
        renderProbe();
        await waitFor(() =>
            expect(screen.getByTestId("lang")).toHaveTextContent("en")
        );

        window.history.replaceState(null, "", "/?lang=ja");
        act(() => {
            window.dispatchEvent(new PopStateEvent("popstate"));
        });

        await waitFor(() =>
            expect(screen.getByTestId("lang")).toHaveTextContent("ja")
        );
    });
});
