/** Rewrite `\(...\)` and `\[...\]` to `$` delimiters before parsing, as remark-math needs. */
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
