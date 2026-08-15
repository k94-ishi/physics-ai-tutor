"use client";

import { FormEvent, useState } from "react";
import Button from "./Button";
import SelectField from "./SelectField";

type PaginationProps = {
    page: number;
    size: number;
    total: number;
    onPageChange: (page: number) => void;
    onSizeChange: (size: number) => void;
    sizeOptions?: number[];
};

const DEFAULT_SIZE_OPTIONS = [30, 60, 120];

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

                <SelectField
                    id="page-size"
                    label="表示件数"
                    value={String(size)}
                    onChange={(e) => onSizeChange(Number(e.target.value))}
                    options={sizeOptions.map((option) => ({
                        value: String(option),
                        label: `${option}件`,
                    }))}
                />
            </div>

            <div className="flex flex-wrap items-center gap-2">
                <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => goTo(page - 1)}
                >
                    前へ
                </Button>

                <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    disabled={page + 2 > lastPage}
                    onClick={() => goTo(page + 2)}
                >
                    2ページ先
                </Button>

                <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    disabled={page + 3 > lastPage}
                    onClick={() => goTo(page + 3)}
                >
                    3ページ先
                </Button>

                <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    disabled={page >= lastPage}
                    onClick={() => goTo(page + 1)}
                >
                    次へ
                </Button>

                <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    disabled={page >= lastPage}
                    onClick={() => goTo(lastPage)}
                >
                    最終ページ
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
