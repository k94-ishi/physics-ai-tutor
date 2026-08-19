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

type LanguageContextValue = {
    language: Language;
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

    // localStorageの読み込みはクライアントでのみ行う(SSR中はwindow不可)。
    useEffect(() => {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored === "ja" || stored === "en") {
                // eslint-disable-next-line react-hooks/set-state-in-effect
                setLanguageState(stored);
            }
        } catch {
            // localStorageが使えない環境(プライベートブラウジング等)は無視する
        }
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
    }, []);

    const t = useCallback(
        (key: TranslationKey, params?: Record<string, string | number>) =>
            interpolate(translations[language][key], params),
        [language]
    );

    return (
        <LanguageContext.Provider value={{ language, setLanguage, t }}>
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
