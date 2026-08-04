import { fetchQuestion } from "@/lib/api";

export default async function QuestionPage(
    {params}: {params: Promise<{ id: string }>}
) {
    const { id } = await params;
    const question = await fetchQuestion(Number(id));

    return (
        <main>
            <h1>
                {question.question}
            </h1>
            
            <p>
                {question.answer}
            </p>
        </main>
    );
}