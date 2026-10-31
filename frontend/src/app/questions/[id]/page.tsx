import AskAiBox from "@/components/AskAiBox";
import QuestionDetail from "@/components/QuestionDetail";

export default async function QuestionPage({
    params,
    searchParams,
}: {
    params: Promise<{ id: string }>;
    searchParams: Promise<{ matched?: string }>;
}) {
    const { id } = await params;
    const { matched } = await searchParams;

    return (
        <main className="flex flex-col gap-6">
            <QuestionDetail id={Number(id)} matched={matched} />

            <AskAiBox />
        </main>
    );
}
