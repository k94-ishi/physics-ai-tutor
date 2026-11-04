"use client";

import { Question } from "@/types/question";
import { useLanguage } from "@/lib/i18n/LanguageContext";

type QuestionLevelGridProps = {
    current: Question;
    items: Question[];
    onPreview: (question: Question) => void;
};

/** Both coordinates are needed to place a QA on the grid. */
export function hasCoordinates(question: Question): boolean {
    return question.physics_level !== null && question.math_level !== null;
}

type Bounds = { minP: number; maxP: number; minM: number; maxM: number };

/** The smallest rectangle holding the current QA and every placeable item. */
export function gridBounds(current: Question, items: Question[]): Bounds {
    const physics = [current, ...items].map((q) => q.physics_level ?? 0);
    const math = [current, ...items].map((q) => q.math_level ?? 0);
    return {
        minP: Math.min(...physics),
        maxP: Math.max(...physics),
        minM: Math.min(...math),
        maxM: Math.max(...math),
    };
}

function cellTone(question: Question, current: Question): string {
    const p = question.physics_level ?? 0;
    const m = question.math_level ?? 0;
    const cp = current.physics_level ?? 0;
    const cm = current.math_level ?? 0;

    // 左下(どちらの軸でも上がらない)は前提側、右上は発展側。
    if (p <= cp && m <= cm) {
        return "border-emerald-200 bg-emerald-50 hover:bg-emerald-100";
    }
    if (p >= cp && m >= cm) {
        return "border-violet-200 bg-violet-50 hover:bg-violet-100";
    }
    return "border-gray-200 bg-gray-50 hover:bg-gray-100";
}

/**
 * 関連QAを物理×数学の難易度平面に並べる([42])。今の質問が自分の座標に
 * 立ち、前提は左下、発展は右上に見える - 「グラフが足場」の見える形。
 * 座標のない行は置けないので、呼び出し側がリストで補う。
 */
export default function QuestionLevelGrid({
    current,
    items,
    onPreview,
}: QuestionLevelGridProps) {
    const { t } = useLanguage();

    const placeable = items.filter(hasCoordinates);
    if (!hasCoordinates(current) || placeable.length === 0) {
        return null;
    }

    const { minP, maxP, minM, maxM } = gridBounds(current, placeable);
    const columns: number[] = [];
    for (let p = minP; p <= maxP; p += 1) columns.push(p);
    const rows: number[] = [];
    for (let m = maxM; m >= minM; m -= 1) rows.push(m);

    const byCell = new Map<string, Question[]>();
    for (const item of placeable) {
        const key = `${item.physics_level}-${item.math_level}`;
        byCell.set(key, [...(byCell.get(key) ?? []), item]);
    }

    return (
        <div className="flex flex-col gap-2">
            <p className="text-xs text-gray-500">{t("grid.hint")}</p>

            <div className="overflow-x-auto">
                <table className="w-full border-separate border-spacing-1">
                    <caption className="sr-only">{t("grid.caption")}</caption>
                    <thead>
                        <tr>
                            <th className="w-10 text-right align-bottom text-xs font-normal text-gray-500">
                                {t("grid.axisMath")}
                            </th>
                            {columns.map((p) => (
                                <th
                                    key={p}
                                    scope="col"
                                    className="pb-1 text-center text-xs font-normal text-gray-500"
                                >
                                    {p}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((m) => (
                            <tr key={m}>
                                <th
                                    scope="row"
                                    className="pr-2 text-right text-xs font-normal text-gray-500"
                                >
                                    {m}
                                </th>
                                {columns.map((p) => {
                                    const here =
                                        current.physics_level === p &&
                                        current.math_level === m;
                                    const cellItems =
                                        byCell.get(`${p}-${m}`) ?? [];
                                    return (
                                        <td
                                            key={p}
                                            className={`min-w-28 rounded-md border align-top ${
                                                here
                                                    ? "border-blue-400 ring-1 ring-blue-300"
                                                    : "border-gray-100"
                                            }`}
                                        >
                                            <div className="flex flex-col gap-1 p-1">
                                                {here && (
                                                    <span className="self-start rounded-full bg-blue-600 px-2 py-0.5 text-[10px] font-semibold text-white">
                                                        {t("grid.current")}
                                                    </span>
                                                )}
                                                {cellItems.map((item) => (
                                                    <button
                                                        key={item.id}
                                                        type="button"
                                                        onClick={() =>
                                                            onPreview(item)
                                                        }
                                                        className={`cursor-pointer rounded-md border px-2 py-1 text-left text-xs text-gray-800 transition-colors ${cellTone(item, current)}`}
                                                    >
                                                        <span className="line-clamp-2">
                                                            {item.question}
                                                        </span>
                                                    </button>
                                                ))}
                                            </div>
                                        </td>
                                    );
                                })}
                            </tr>
                        ))}
                    </tbody>
                    <tfoot>
                        <tr>
                            <td />
                            <td
                                colSpan={columns.length}
                                className="pt-1 text-center text-xs text-gray-500"
                            >
                                {t("grid.axisPhysics")}
                            </td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        </div>
    );
}
