import type { Metadata } from "next";
import type { ReactNode } from "react";

// The rest of the site is noindex (see the root layout); the privacy policy
// must stay reachable by crawlers because the Google OAuth consent screen
// links to it.
export const metadata: Metadata = {
    title: "Privacy Policy | Physics AI Tutor",
    robots: {
        index: true,
        follow: false,
    },
};

export default function PrivacyLayout({ children }: { children: ReactNode }) {
    return children;
}
