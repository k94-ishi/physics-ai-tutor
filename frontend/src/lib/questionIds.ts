/**
 * 管理画面のキーワード入力でID検索を受け付けるためのパーサ。
 * `#54`、`id:54`、`#54, 848` のいずれも同じid一覧として扱い、
 * それ以外の文字列は通常のキーワード検索として扱う（nullを返す）。
 */

const ID_TOKEN = /^(?:#|id:)?(\d+)$/i;

/** Max ids the API accepts in one `ids` parameter. */
export const MAX_ID_SEARCH = 100;

export function parseIdSearch(input: string): number[] | null {
    const trimmed = input.trim();
    if (!trimmed) {
        return null;
    }

    // An id search must look like one from the start, so plain keywords
    // containing a number (for example "運動量 2") stay keyword searches.
    if (
        !/^(?:#|id:)/i.test(trimmed) &&
        !/^\d+(?:\s*,\s*\d+)*\s*,?$/.test(trimmed)
    ) {
        return null;
    }

    // A trailing comma is a normal artefact of pasting a list.
    const tokens = trimmed
        .split(",")
        .map((token) => token.trim())
        .filter((token) => token !== "");
    const ids: number[] = [];

    for (const token of tokens) {
        const match = ID_TOKEN.exec(token);
        if (!match) {
            return null;
        }

        const id = Number(match[1]);
        if (!Number.isSafeInteger(id) || id <= 0) {
            return null;
        }
        if (!ids.includes(id)) {
            ids.push(id);
        }
    }

    return ids.length > 0 && ids.length <= MAX_ID_SEARCH ? ids : null;
}
