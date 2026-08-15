import QuestionList from "@/components/QuestionList";


export default function Home() {
  return (
    <main className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold text-gray-900">
        学習データベース
      </h1>

      <QuestionList />
    </main>
  );
}
