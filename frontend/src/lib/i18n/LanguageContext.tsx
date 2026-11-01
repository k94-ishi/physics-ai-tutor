"use client";

import {
    createContext,
    ReactNode,
    useCallback,
    useContext,
    useEffect,
    useState,
} from "react";
import { translations, TranslationKey } from "@/lib/i18n/translations";

export type Language = "ja" | "en";

const STORAGE_KEY = "language";

// URLの?lang=を読む([50])。useSearchParamsを使わないのは、ルート直下の
// プロバイダで使うと全ページがSuspense/動的化を要求されるため。言語解決は
// 元々クライアントのマウント時処理なので、URLも同じ場所で読む。
function readUrlLanguage(): Language | null {
    try {
        const value = new URLSearchParams(window.location.search).get("lang");
        return value === "ja" || value === "en" ? value : null;
    } catch {
        return null;
    }
}

type LanguageContextValue = {
    language: Language;
    /** URL/localStorageの解決が済んだか。言語に依存する副作用(検索の復元
     * など)はこれを待たないと、既定のjaで一度走ってから走り直してしまう。 */
    resolved: boolean;
    setLanguage: (language: Language) => void;
    t: (key: TranslationKey, params?: Record<string, string | number>) => string;
};

const LanguageContext = createContext<LanguageContextValue | undefined>(
    undefined
);

function interpolate(
    template: string,
    params?: Record<string, string | number>
): string {
    if (!params) {
        return template;
    }
    return template.replace(/\{(\w+)\}/g, (match, key) =>
        key in params ? String(params[key]) : match
    );
}

export function LanguageProvider({ children }: { children: ReactNode }) {
    const [language, setLanguageState] = useState<Language>("ja");
    const [resolved, setResolved] = useState(false);

    // 言語の優先順位([50]): URLの?lang= > localStorage > 既定のja。
    // URL指定はそのリンクを見ている間だけの一時的なもので、保存済みの
    // 好みは上書きしない(明示的な切替だけが保存される)。
    // クライアントでのみ行う(SSR中はwindow不可)。
    useEffect(() => {
        const fromUrl = readUrlLanguage();
        if (fromUrl !== null) {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setLanguageState(fromUrl);
            return;
        }

        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored === "ja" || stored === "en") {
                 
                setLanguageState(stored);
            }
        } catch {
            // localStorageが使えない環境(プライベートブラウジング等)は無視する
        }
    }, []);

    // fromUrlの早期returnがあるため、resolvedは別のeffectで必ず立てる。
    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setResolved(true);
    }, []);

    // 戻る/進むで?lang=付きのURLに戻ったら、そのリンクの言語に合わせ直す。
    useEffect(() => {
        const handlePopState = () => {
            const fromUrl = readUrlLanguage();
            if (fromUrl !== null) {
                setLanguageState(fromUrl);
            }
        };

        window.addEventListener("popstate", handlePopState);
        return () => window.removeEventListener("popstate", handlePopState);
    }, []);

    useEffect(() => {
        document.documentElement.lang = language;
    }, [language]);

    const setLanguage = useCallback((next: Language) => {
        setLanguageState(next);
        try {
            localStorage.setItem(STORAGE_KEY, next);
        } catch {
            // 保存できなくても表示切替自体は継続する
        }

        // ?lang=付きのリンクを見ている間に切り替えたら、URLも追従させる
        // (共有・リロードしても今見ている言語のまま)。パラメータがない
        // 普段のURLには足さない。Next 14+が公式に認めるshallow更新。
        try {
            const url = new URL(window.location.href);
            if (url.searchParams.get("lang") !== null) {
                url.searchParams.set("lang", next);
                window.history.replaceState(window.history.state, "", url);
            }
        } catch {
            // URLを触れない環境でも表示切替自体は継続する
        }
    }, []);

    const t = useCallback(
        (key: TranslationKey, params?: Record<string, string | number>) =>
            interpolate(translations[language][key], params),
        [language]
    );

    return (
        <LanguageContext.Provider value={{ language, resolved, setLanguage, t }}>
            {children}
        </LanguageContext.Provider>
    );
}

export function useLanguage(): LanguageContextValue {
    const context = useContext(LanguageContext);

    if (context === undefined) {
        throw new Error("useLanguage must be used within a LanguageProvider");
    }

    return context;
}
