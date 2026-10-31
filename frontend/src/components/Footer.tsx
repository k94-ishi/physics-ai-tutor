import Link from "next/link";
import T from "@/components/ui/T";

export default function Footer() {
    return (
        <footer className="border-t border-gray-200 bg-white">
            <div className="mx-auto flex w-full max-w-4xl items-center justify-between px-3 py-4 text-xs text-gray-500">
                <span>Physics AI Tutor</span>
                <Link href="/privacy" className="hover:text-gray-700">
                    <T k="footer.privacy" />
                </Link>
            </div>
        </footer>
    );
}
