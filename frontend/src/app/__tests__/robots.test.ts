import { describe, expect, it } from "vitest";
import robots from "@/app/robots";

describe("robots.txt", () => {
    it("allows /privacy while keeping the rest of the site disallowed", () => {
        expect(robots()).toEqual({
            rules: {
                userAgent: "*",
                allow: "/privacy",
                disallow: "/",
            },
        });
    });
});
