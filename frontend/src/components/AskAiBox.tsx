"use client";

import QuestionSearchAndAsk from "@/components/QuestionSearchAndAsk";

export default function AskAiBox() {
    return (
        <div className="flex flex-col gap-3">
            <h2 className="text-lg font-semibold text-gray-900">
                AIに質問する
            </h2>

            <QuestionSearchAndAsk />
        </div>
    );
}
