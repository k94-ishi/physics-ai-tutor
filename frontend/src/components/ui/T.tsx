"use client";

import { useLanguage } from "@/lib/i18n/LanguageContext";
import { TranslationKey } from "@/lib/i18n/translations";

type TProps = {
    k: TranslationKey;
    params?: Record<string, string | number>;
};

/**
 * Renders a translated string. Exists so Server Components (which can't
 * call the useLanguage hook themselves) can still show translated text by
 * rendering this Client Component as a leaf.
 */
export default function T({ k, params }: TProps) {
    const { t } = useLanguage();
    return t(k, params);
}
