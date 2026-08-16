"use client";

import Link from "next/link";
import { RetrievedQuestionRef } from "@/types/question";

type ReferencedQuestionsProps = {
    items: RetrievedQuestionRef[];
};

/**
 * RAG生成結果のカード下部に表示する「参考にしたQA」一覧。通常QAとの
 * 差分を示すため、本文とは別フォント(font-serif)で表示する。
 */
export default function ReferencedQuestions({ items }: ReferencedQuestionsProps) {
    if (items.length === 0) {
        return null;
    }

    return (
        <div
            className="flex flex-col gap-1 border-t border-gray-100 pt-2"
            onClick={(e) => e.stopPropagation()}
        >
            <p className="font-serif text-xs text-gray-500">
                回答生成時に参考にしたQA:
            </p>

            <ul className="flex flex-col gap-0.5">
                {items.map((item) => (
                    <li key={item.id} className="font-serif text-xs text-gray-500">
                        <Link
                            href={`/questions/${item.id}`}
                            className="hover:underline"
                        >
                            ・{item.question}
                        </Link>
                    </li>
                ))}
            </ul>
        </div>
    );
}
