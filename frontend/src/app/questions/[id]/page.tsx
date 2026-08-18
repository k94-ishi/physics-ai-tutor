import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiError, fetchQuestion, fetchRelatedQuestions } from "@/lib/api";
import { Question } from "@/types/question";
import Card from "@/components/ui/Card";
import MarkdownContent from "@/components/ui/MarkdownContent";
import ReferencedQuestions from "@/components/ui/ReferencedQuestions";
import AskAiBox from "@/components/AskAiBox";

export default async function QuestionPage(
    {
        params,
        searchParams,
    }: {
        params: Promise<{ id: string }>;
        searchParams: Promise<{ matched?: string }>;
    }
) {
    const { id } = await params;
    const { matched } = await searchParams;

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
                {matched === "exact" && (
                    <p className="rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-700">
                        この質問に対する回答はすでに生成済みです
                    </p>
                )}

                <div className="flex flex-wrap items-center gap-2">
                    {question.status === "UNREVIEWED" && (
                        <span className="shrink-0 rounded-full bg-yellow-50 px-2 py-0.5 text-xs font-medium text-yellow-700">
                            管理者未チェック
                        </span>
                    )}

                    <h1 className="text-xl font-bold text-gray-900">
                        {question.question}
                    </h1>
                </div>

                <MarkdownContent content={question.answer} variant="full" />

                <ReferencedQuestions items={question.retrieved_questions} />
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

                                    <MarkdownContent
                                        content={related.answer}
                                        variant="preview"
                                    />
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
