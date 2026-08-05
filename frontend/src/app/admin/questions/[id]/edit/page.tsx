"use client";

import {
    SyntheticEvent,
    useCallback,
    useEffect,
    useState,
} from "react";
import { useParams, useRouter } from "next/navigation";
import { fetchQuestion, updateQuestion } from "@/lib/api";


export default function EditQuestionPage() {
    const router = useRouter();
    const params = useParams();
    const id = Number(params.id);
    const [question, setQuestion] = useState("");
    const [answer, setAnswer] = useState("");
    const [loading, setLoading] = useState(true);
    const loadQuestion = useCallback(async () => {
        try {
            const data = await fetchQuestion(id);
            setQuestion(data.question);
            setAnswer(data.answer);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    }, [id]);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        loadQuestion();
    }, [loadQuestion]);

    const handleSubmit = async (
        e: SyntheticEvent<HTMLFormElement>
    ) => {
        e.preventDefault();
        try {
            await updateQuestion({
                id,
                question,
                answer,
            });
            alert("更新しました。");
            router.push("/admin/questions");
        } catch (error) {
            console.error(error);
            alert("更新に失敗しました。");
        }
    };

    if (loading) {
        return <div>Loading...</div>
    }

    return (
        <main>
            <h1>質問編集</h1>
            <form onSubmit={handleSubmit}>
                <div>
                    <label>質問</label>
                    <textarea
                    value={question}
                    onChange={(e) =>
                        setQuestion(e.target.value)
                    }/>
                </div>

                <div>
                    <label>回答</label>
                    <textarea
                    value={answer}
                    onChange={(e) =>
                        setAnswer(e.target.value)
                    }/>
                </div>

                <button type="submit">保存</button>
            </form>
        </main>
    );
}
