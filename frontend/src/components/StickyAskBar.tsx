"use client";

import { ReactNode, useEffect, useRef, useState } from "react";

/** 他の固定要素(トースト)が重ならないよう、実測した高さを共有する。 */
export const ASK_BAR_HEIGHT_VAR = "--ask-bar-height";

type StickyAskBarProps = {
    children: ReactNode;
};

/**
 * 画面下に貼り付く質問バー([43])。長い回答を読んでいる途中でも、
 * 戻らずにその場で検索・質問できるようにする。
 *
 * 高さは内容(検索結果やAI回答)で変わるので固定値を置かず、ResizeObserverで
 * 実測して (a) 本文を隠さないためのスペーサーと (b) トーストのオフセット用
 * CSS変数に反映する。背が高くなりすぎないよう上限を付けて内部スクロールにする。
 */
export default function StickyAskBar({ children }: StickyAskBarProps) {
    const barRef = useRef<HTMLDivElement>(null);
    const [height, setHeight] = useState(0);

    useEffect(() => {
        const node = barRef.current;
        if (node === null) {
            return;
        }

        const apply = (next: number) => {
            setHeight(next);
            document.documentElement.style.setProperty(
                ASK_BAR_HEIGHT_VAR,
                `${next}px`
            );
        };

        apply(node.getBoundingClientRect().height);

        // jsdomにResizeObserverがない環境でも初期測定だけで動くようにする。
        if (typeof ResizeObserver === "undefined") {
            return () => {
                document.documentElement.style.removeProperty(ASK_BAR_HEIGHT_VAR);
            };
        }

        const observer = new ResizeObserver((entries) => {
            apply(entries[0].contentRect.height);
        });
        observer.observe(node);

        return () => {
            observer.disconnect();
            document.documentElement.style.removeProperty(ASK_BAR_HEIGHT_VAR);
        };
    }, []);

    return (
        <>
            {/* 本文の最後がバーの裏に隠れないよう、同じ高さだけ場所を空ける。 */}
            <div aria-hidden="true" style={{ height }} />

            <div
                ref={barRef}
                data-testid="sticky-ask-bar"
                className="fixed inset-x-0 bottom-0 z-40 border-t border-gray-200 bg-white/95 shadow-[0_-2px_8px_rgba(0,0,0,0.06)] backdrop-blur"
            >
                <div
                    className="mx-auto w-full max-w-4xl overflow-y-auto px-3 py-3"
                    style={{
                        // 画面を覆い尽くさない範囲で結果も見せる。
                        maxHeight: "70svh",
                        // iOSのホームインジケータ等を避ける。
                        paddingBottom: "calc(0.75rem + env(safe-area-inset-bottom))",
                    }}
                >
                    {children}
                </div>
            </div>
        </>
    );
}
