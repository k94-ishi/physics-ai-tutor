import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";
import PrivacyPage from "@/app/privacy/page";

function renderPage() {
    return render(
        <LanguageProvider>
            {/* The language select mirrors the header's control. */}
            <PrivacyPage />
        </LanguageProvider>
    );
}

describe("PrivacyPage", () => {
    it("renders every section in Japanese by default", () => {
        renderPage();

        expect(
            screen.getByRole("heading", { name: "プライバシーポリシー" })
        ).toBeInTheDocument();

        for (const heading of [
            "保存する情報",
            "収集しない情報",
            "利用目的",
            "外部サービスへの提供",
            "保存期間",
            "アカウントの削除",
            "お問い合わせ",
            "本ポリシーの変更",
        ]) {
            expect(
                screen.getByRole("heading", { name: heading })
            ).toBeInTheDocument();
        }
    });

    it("links to a contact channel", () => {
        renderPage();

        const link = screen.getByRole("link", { name: "お問い合わせ窓口" });
        expect(link).toHaveAttribute(
            "href",
            expect.stringContaining("github.com/k94-ishi/physics-ai-tutor")
        );
    });

    it("mentions what sign-in stores, matching the backend schema", () => {
        renderPage();

        // users: email + google_sub; rate_limit_hits: pruned after ~1 day.
        expect(screen.getByText(/メールアドレス、Googleアカウントの識別子/)).toBeInTheDocument();
        expect(screen.getByText(/約1日で自動削除/)).toBeInTheDocument();
    });
});

describe("PrivacyPage in English", () => {
    afterEach(() => {
        localStorage.clear();
    });

    it("renders the English sections when English is the stored language", async () => {
        localStorage.setItem("language", "en");

        renderPage();

        expect(
            await screen.findByRole("heading", { name: "Privacy Policy" })
        ).toBeInTheDocument();
        expect(
            screen.getByRole("heading", { name: "Information we store" })
        ).toBeInTheDocument();
        expect(screen.getByText(/deleted automatically after about one day/))
            .toBeInTheDocument();
    });
});
