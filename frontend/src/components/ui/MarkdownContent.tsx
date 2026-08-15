"use client";

import { ComponentProps, ReactNode } from "react";
import ReactMarkdown, { type ExtraProps } from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import { normalizeMathDelimiters } from "@/lib/markdown";
import MermaidDiagram from "./MermaidDiagram";

type Variant = "full" | "preview";

type MarkdownContentProps = {
    content: string;
    variant?: Variant;
    clampLines?: 2 | 3 | 4;
};

const CLAMP_CLASSES: Record<number, string> = {
    2: "line-clamp-2",
    3: "line-clamp-3",
    4: "line-clamp-4",
};

function CodeBlock({
    className,
    children,
    variant,
}: ComponentProps<"code"> & ExtraProps & { variant: Variant }) {
    const language = /language-(\w+)/.exec(className ?? "")?.[1];

    if (language === "mermaid") {
        if (variant === "preview") {
            return (
                <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                    図を含む
                </span>
            );
        }

        return <MermaidDiagram code={String(children).trim()} />;
    }

    return (
        <code className="rounded bg-gray-100 px-1 py-0.5 text-[0.85em]">
            {children}
        </code>
    );
}

function Paragraph({ children }: { children?: ReactNode }) {
    return <p className="mb-2 last:mb-0">{children}</p>;
}

function UnorderedList({ children }: { children?: ReactNode }) {
    return <ul className="mb-2 list-disc pl-5 last:mb-0">{children}</ul>;
}

function OrderedList({ children }: { children?: ReactNode }) {
    return <ol className="mb-2 list-decimal pl-5 last:mb-0">{children}</ol>;
}

/**
 * 質問・回答テキストをMarkdown(表・数式・Mermaid図解)として描画する共通コンポーネント。
 * variant="preview"は一覧カードでの短い抜粋表示用で、Mermaid図は重い描画を避けて
 * プレースホルダーに置き換える。
 */
export default function MarkdownContent({
    content,
    variant = "full",
    clampLines = 3,
}: MarkdownContentProps) {
    return (
        <div
            className={`text-sm text-gray-700 ${
                variant === "preview" ? CLAMP_CLASSES[clampLines] : ""
            }`}
        >
            <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex]}
                components={{
                    p: Paragraph,
                    ul: UnorderedList,
                    ol: OrderedList,
                    code: (props) => <CodeBlock {...props} variant={variant} />,
                }}
            >
                {normalizeMathDelimiters(content)}
            </ReactMarkdown>
        </div>
    );
}
