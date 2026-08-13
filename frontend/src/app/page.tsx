import QuestionList from "@/components/QuestionList";
import AskAiBox from "@/components/AskAiBox";


export default function Home() {
  return (
    <main className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold text-gray-900">
        Physics AI Tutor
      </h1>

      <AskAiBox />

      <QuestionList />
    </main>
  );
}