"use client";

import { SyntheticEvent, useState } from "react";
import { createQuestion } from "@/lib/api";


export default function NewQuestionPage() {
    const [question, setQuestion] = useState("");
    const [answer, setAnswer] = useState("");
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (
        e: SyntheticEvent<HTMLFormElement>
    ) => {
        e.preventDefault();
        setLoading(true);
        try {
            await createQuestion({
                question,
                answer,
            });

            alert("登録しました。");

            // フォームを初期化
            setQuestion("");
            setAnswer("");
        } catch (error) {
            console.error(error);
            alert("登録に失敗しました。");
        } finally {
            setLoading(false);
        }
    };

    return (
        <main>
            <h1>
                質問登録
            </h1>
            <form
                onSubmit={handleSubmit}
            >
                <div>
                    <label>
                        質問
                    </label>

                    <textarea
                        value={question}
                        onChange={(e) =>
                            setQuestion(
                                e.target.value
                            )
                        }
                    />
                </div>

                <div>
                    <label>
                        回答
                    </label>

                    <textarea
                        value={answer}
                        onChange={(e) =>
                            setAnswer(
                                e.target.value
                            )
                        }
                    />
                </div>

                <button
                    type="submit"
                    disabled={loading}
                >
                    {loading 
                        ? "登録中..."
                        : "登録"}
                </button>
            </form>
        </main>
    )
}