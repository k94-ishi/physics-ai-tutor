import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiError, fetchQuestion, fetchRelatedQuestions } from "@/lib/api";
import { Question } from "@/types/question";
import Card from "@/components/ui/Card";
import AskAiBox from "@/components/AskAiBox";

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

    let relatedQuestions: Question[];
    try {
        relatedQuestions = await fetchRelatedQuestions(Number(id));
    } catch (error) {
        console.error(error);
        relatedQuestions = [];
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

            {relatedQuestions.length > 0 && (
                <div className="flex flex-col gap-3">
                    <h2 className="text-lg font-semibold text-gray-900">
                        関連する質問
                    </h2>

                    <div className="flex flex-col gap-3">
                        {relatedQuestions.map((related) => (
                            <Link key={related.id} href={`/questions/${related.id}`}>
                                <Card className="transition-colors hover:border-blue-300 hover:bg-blue-50/50">
                                    <span className="font-medium text-gray-900">
                                        {related.question}
                                    </span>

                                    <p className="mt-1 line-clamp-3 text-sm text-gray-600">
                                        {related.answer}
                                    </p>
                                </Card>
                            </Link>
                        ))}
                    </div>
                </div>
            )}

            <AskAiBox />
        </main>
    );
}
