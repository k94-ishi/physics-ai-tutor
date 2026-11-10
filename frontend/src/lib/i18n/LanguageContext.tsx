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

// Read `?lang=` here, not with useSearchParams, which would make every page dynamic ([50]).
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
    /** Whether the language is resolved; wait for it, or effects run once in ja first. */
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

    // Priority `?lang=` > localStorage > ja; a link's language is never stored ([50]).
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
            // localStorage may be unavailable (private browsing).
        }
    }, []);

    // Set `resolved` in its own effect, because the URL branch returns early.
    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setResolved(true);
    }, []);

    // Back/forward to a `?lang=` URL re-applies that link's language.
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
            // Switching still works when saving fails.
        }

        // While a `?lang=` link is open, a switch updates the URL too; plain URLs stay plain.
        try {
            const url = new URL(window.location.href);
            if (url.searchParams.get("lang") !== null) {
                url.searchParams.set("lang", next);
                window.history.replaceState(window.history.state, "", url);
            }
        } catch {
            // Switching still works when the URL cannot be changed.
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
