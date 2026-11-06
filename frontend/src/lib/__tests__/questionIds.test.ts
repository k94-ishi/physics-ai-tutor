import { describe, expect, it } from "vitest";
import { MAX_ID_SEARCH, parseIdSearch } from "@/lib/questionIds";

describe("parseIdSearch", () => {
    it("accepts the forms an issue or eval case would be quoted as", () => {
        expect(parseIdSearch("#54")).toEqual([54]);
        expect(parseIdSearch("id:54")).toEqual([54]);
        expect(parseIdSearch("ID:54")).toEqual([54]);
        expect(parseIdSearch("54")).toEqual([54]);
        expect(parseIdSearch("  #54  ")).toEqual([54]);
    });

    it("accepts a pasted list and keeps the given order", () => {
        expect(parseIdSearch("54,848")).toEqual([54, 848]);
        expect(parseIdSearch("#54, 848")).toEqual([54, 848]);
        expect(parseIdSearch("848,54")).toEqual([848, 54]);
    });

    it("drops duplicates so the total matches the card count", () => {
        expect(parseIdSearch("54,54,848")).toEqual([54, 848]);
    });

    it("treats ordinary keywords as keywords, not ids", () => {
        expect(parseIdSearch("運動量")).toBeNull();
        expect(parseIdSearch("運動量 2")).toBeNull();
        expect(parseIdSearch("")).toBeNull();
        expect(parseIdSearch("   ")).toBeNull();
        expect(parseIdSearch("#")).toBeNull();
        expect(parseIdSearch("#abc")).toBeNull();
        expect(parseIdSearch("#54 848")).toBeNull();
        expect(parseIdSearch("54,")).toEqual([54]);
    });

    it("rejects ids the API would refuse", () => {
        expect(parseIdSearch("#0")).toBeNull();
        expect(parseIdSearch("#-1")).toBeNull();
        expect(parseIdSearch("#1.5")).toBeNull();
        const tooMany = Array.from(
            { length: MAX_ID_SEARCH + 1 },
            (_, i) => i + 1
        ).join(",");
        expect(parseIdSearch(tooMany)).toBeNull();
    });
});
