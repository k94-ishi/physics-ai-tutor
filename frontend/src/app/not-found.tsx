import Link from "next/link";
import { buttonClassName } from "@/components/ui/Button";
import T from "@/components/ui/T";

export default function NotFound() {
    return (
        <main className="flex flex-col items-start gap-4">
            <h1 className="text-xl font-bold text-gray-900">
                <T k="notFound.title" />
            </h1>

            <p className="text-sm text-gray-600">
                <T k="notFound.description" />
            </p>

            <Link href="/" className={buttonClassName("primary")}>
                <T k="notFound.backHome" />
            </Link>
        </main>
    );
}
