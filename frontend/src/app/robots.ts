import type { MetadataRoute } from "next";

// The site stays out of search engines, but the privacy policy must be
// fetchable: the Google OAuth consent screen links to it and its check
// never sees the page's own robots metadata if robots.txt blocks the
// crawl. Most-specific path wins, so Allow beats the general Disallow.
// Add "/help" here once the usage guide ships.
export default function robots(): MetadataRoute.Robots {
    return {
        rules: {
            userAgent: "*",
            allow: "/privacy",
            disallow: "/",
        },
    };
}
