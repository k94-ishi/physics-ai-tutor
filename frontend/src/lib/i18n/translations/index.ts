// Simple dictionary-based translations. Not a full i18n library - flat,
// dot-namespaced keys map directly to strings, with {placeholder}
// interpolation handled by LanguageContext's `t()`. `en` is typed against
// `keyof typeof ja` so adding a key to one side without the other is a
// compile error.
//
// The table is split by feature ([64]); each file pairs its `ja` with an
// `en` typed against it, and the merged table below is what `t()` reads.

import * as common from "@/lib/i18n/translations/common";
import * as student from "@/lib/i18n/translations/student";
import * as account from "@/lib/i18n/translations/account";
import * as admin from "@/lib/i18n/translations/admin";
import * as adminStats from "@/lib/i18n/translations/adminStats";
import * as levels from "@/lib/i18n/translations/levels";
import * as conceptsAdmin from "@/lib/i18n/translations/conceptsAdmin";

const ja = {
    ...common.ja,
    ...student.ja,
    ...account.ja,
    ...admin.ja,
    ...adminStats.ja,
    ...levels.ja,
    ...conceptsAdmin.ja,
} as const;

const en: Record<keyof typeof ja, string> = {
    ...common.en,
    ...student.en,
    ...account.en,
    ...admin.en,
    ...adminStats.en,
    ...levels.en,
    ...conceptsAdmin.en,
};

export const translations = { ja, en };
export type TranslationKey = keyof typeof ja;
