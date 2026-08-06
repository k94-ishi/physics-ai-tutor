import { notFound } from "next/navigation";
import { ApiError, fetchQuestion } from "@/lib/api";
import Card from "@/components/ui/Card";

export default async function QuestionPage(
    {params}: {params: Promise<{ id: string }>}
) {
    const { id } = await params;

    let question;
    try {
        question = await fetchQuestion(Number(id));
    } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
            notFound();
        }
        throw error;
    }

    return (
        <main className="flex flex-col gap-6">
            <Card className="flex flex-col gap-4">
                <h1 className="text-xl font-bold text-gray-900">
                    {question.question}
                </h1>

                <p className="whitespace-pre-wrap text-gray-700">
                    {question.answer}
                </p>
            </Card>
        </main>
    );
}
