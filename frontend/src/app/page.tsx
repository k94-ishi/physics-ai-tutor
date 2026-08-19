import QuestionList from "@/components/QuestionList";
import T from "@/components/ui/T";


export default function Home() {
  return (
    <main className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold text-gray-900">
        <T k="home.heading" />
      </h1>

      <QuestionList />
    </main>
  );
}
