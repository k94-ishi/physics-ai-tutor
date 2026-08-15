/**
 * remark-mathは`$...$`/`$$...$$`しか数式として認識しないが、DeepSeekの回答は
 * `\(...\)`(インライン)・`\[...\]`(ブロック)というLaTeXネイティブな区切りを
 * 使うことがある。remark-parseの時点でCommonMarkのバックスラッシュエスケープ
 * 規則により`\(`等の情報が失われるため、構文木を見てから変換することはできず、
 * remark-parseに渡す前の生の文字列を書き換える必要がある。
 * (参考: assistant-uiのnormalizeMathDelimitersと同じアプローチ)
 */
export function normalizeMathDelimiters(content: string): string {
    return content
        .replace(
            /\\{1,2}\[([\s\S]+?)\\{1,2}\]/g,
            (_, expr: string) => `$$${expr.trim()}$$`
        )
        .replace(
            /\\{1,2}\(([^\n]+?)\\{1,2}\)/g,
            (_, expr: string) => `$${expr.trim()}$`
        );
}
