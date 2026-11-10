"use client";

import { ReactNode, useEffect, useRef, useState } from "react";

/** Shares the bar's measured height so toasts can sit above it. */
export const ASK_BAR_HEIGHT_VAR = "--ask-bar-height";

type StickyAskBarProps = {
    children: ReactNode;
};

/** Ask bar fixed to the bottom of the question page; it measures itself and reserves its height ([43]). */
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

        // Without ResizeObserver (jsdom) the first measurement still works.
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
            {/* Reserve the bar's height so the end of the answer is never hidden. */}
            <div aria-hidden="true" style={{ height }} />

            <div
                ref={barRef}
                data-testid="sticky-ask-bar"
                className="fixed inset-x-0 bottom-0 z-40 border-t border-gray-200 bg-white/95 shadow-[0_-2px_8px_rgba(0,0,0,0.06)] backdrop-blur"
            >
                <div
                    className="mx-auto w-full max-w-4xl overflow-y-auto px-3 py-3"
                    style={{
                        // Cap the height so results show without covering the screen.
                        maxHeight: "70svh",
                        // Keep clear of the iOS home indicator.
                        paddingBottom: "calc(0.75rem + env(safe-area-inset-bottom))",
                    }}
                >
                    {children}
                </div>
            </div>
        </>
    );
}
