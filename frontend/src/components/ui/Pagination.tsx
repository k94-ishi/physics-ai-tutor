"use client";

import { FormEvent, useState } from "react";
import Button from "./Button";

type PaginationProps = {
    page: number;
    size: number;
    total: number;
    onPageChange: (page: number) => void;
    onSizeChange: (size: number) => void;
    sizeOptions?: number[];
};

const DEFAULT_SIZE_OPTIONS = [30, 60, 120];

type PageItem = number | "ellipsis";

function getPageItems(page: number, lastPage: number, delta = 2): PageItem[] {
    const pages = new Set<number>([1, lastPage]);
    for (let p = page - delta; p <= page + delta; p++) {
        if (p >= 1 && p <= lastPage) pages.add(p);
    }
    const sorted = [...pages].sort((a, b) => a - b);
    const items: PageItem[] = [];
    let prev = 0;
    for (const p of sorted) {
        if (prev && p - prev > 1) items.push("ellipsis");
        items.push(p);
        prev = p;
    }
    return items;
}

export default function Pagination({
    page,
    size,
    total,
    onPageChange,
    onSizeChange,
    sizeOptions = DEFAULT_SIZE_OPTIONS,
}: PaginationProps) {
    const [jumpInput, setJumpInput] = useState("");
    const lastPage = Math.max(1, Math.ceil(total / size));
    const rangeStart = total === 0 ? 0 : (page - 1) * size + 1;
    const rangeEnd = Math.min(page * size, total);

    function goTo(target: number) {
        onPageChange(Math.min(lastPage, Math.max(1, target)));
    }

    function handleJumpSubmit(e: FormEvent<HTMLFormElement>) {
        e.preventDefault();
        const target = Number(jumpInput);
        if (Number.isFinite(target) && target >= 1) {
            goTo(target);
        }
        setJumpInput("");
    }

    return (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4">
                <span className="text-sm text-gray-500">
                    {rangeStart}–{rangeEnd}件 / 全{total}件
                </span>

                <div className="flex items-center gap-1.5">
                    <label
                        htmlFor="page-size"
                        className="text-sm text-gray-500"
                    >
                        表示件数
                    </label>
                    <select
                        id="page-size"
                        value={String(size)}
                        onChange={(e) => onSizeChange(Number(e.target.value))}
                        className="rounded-md border border-gray-300 bg-white px-2 py-1 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    >
                        {sizeOptions.map((option) => (
                            <option key={option} value={option}>
                                {option}件
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
                <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => goTo(page - 1)}
                    aria-label="前のページ"
                >
                    &lt;
                </Button>

                {getPageItems(page, lastPage).map((item, index) =>
                    item === "ellipsis" ? (
                        <span
                            key={`ellipsis-${index}`}
                            className="px-1 text-sm text-gray-400"
                        >
                            …
                        </span>
                    ) : (
                        <Button
                            key={item}
                            type="button"
                            variant={item === page ? "primary" : "secondary"}
                            size="sm"
                            onClick={() => goTo(item)}
                            aria-current={item === page ? "page" : undefined}
                        >
                            {item}
                        </Button>
                    )
                )}

                <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    disabled={page >= lastPage}
                    onClick={() => goTo(page + 1)}
                    aria-label="次のページ"
                >
                    &gt;
                </Button>

                <form
                    onSubmit={handleJumpSubmit}
                    className="flex items-center gap-1"
                >
                    <input
                        type="number"
                        min={1}
                        max={lastPage}
                        placeholder={`${page}`}
                        value={jumpInput}
                        onChange={(e) => setJumpInput(e.target.value)}
                        className="w-16 rounded-md border border-gray-300 px-2 py-1 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        aria-label="ページ番号を直接入力"
                    />
                    <Button type="submit" variant="secondary" size="sm">
                        移動
                    </Button>
                </form>
            </div>
        </div>
    );
}
