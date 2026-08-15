"use client";

import { useEffect, useId, useRef, useState } from "react";

type MermaidDiagramProps = {
    code: string;
};

export default function MermaidDiagram({ code }: MermaidDiagramProps) {
    const diagramId = useId().replace(/:/g, "");
    const containerRef = useRef<HTMLDivElement>(null);
    const [hasError, setHasError] = useState(false);

    useEffect(() => {
        let cancelled = false;

        (async () => {
            setHasError(false);

            try {
                const { default: mermaid } = await import("mermaid");
                mermaid.initialize({ startOnLoad: false, theme: "neutral" });
                const { svg } = await mermaid.render(
                    `mermaid-${diagramId}`,
                    code
                );
                if (!cancelled && containerRef.current) {
                    containerRef.current.innerHTML = svg;
                }
            } catch (error) {
                console.error("Failed to render mermaid diagram", error);
                if (!cancelled) {
                    setHasError(true);
                }
            }
        })();

        return () => {
            cancelled = true;
        };
    }, [code, diagramId]);

    if (hasError) {
        return (
            <p className="my-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
                図を表示できませんでした。
            </p>
        );
    }

    return (
        <div
            ref={containerRef}
            className="my-2 flex justify-center overflow-x-auto"
        />
    );
}
