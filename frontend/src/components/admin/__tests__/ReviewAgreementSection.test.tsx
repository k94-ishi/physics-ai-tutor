import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ReviewAgreementResponse } from "@/types/question";

vi.mock("@/lib/api", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@/lib/api")>();
    return { ...actual, fetchReviewAgreement: vi.fn() };
});

import * as api from "@/lib/api";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";
import ReviewAgreementSection from "@/components/admin/ReviewAgreementSection";

const mocked = vi.mocked(api);

const METRICS = {
    n: 10,
    sufficient: false,
    exact_agreement_rate: 0.6,
    publish_agreement_rate: 0.7,
    reject_precision: 0.75,
    reject_recall: 0.6,
    reason_jaccard_mean: 0.5,
    confusion_matrix: {
        APPROVE: { APPROVE: 2, EDIT_APPROVE: 0, REJECT: 1 },
        EDIT: { APPROVE: 1, EDIT_APPROVE: 1, REJECT: 0 },
        REJECT: { APPROVE: 1, EDIT_APPROVE: 0, REJECT: 3 },
        UNPARSED: { APPROVE: 0, EDIT_APPROVE: 0, REJECT: 1 },
    },
    calibration: [
        { low: 0.9, high: 1.0, n: 2, agreement_rate: 1.0 },
        { low: 0.6, high: 0.7, n: 2, agreement_rate: 0.5 },
    ],
};

const REPORT: ReviewAgreementResponse = {
    since: "2026-10-28T00:00:00Z",
    overall: METRICS,
    by_answer_prompt_version: { v2: METRICS },
    by_reviewer_prompt_version: { r1: METRICS, r2: { ...METRICS, n: 40, sufficient: true } },
    by_month: { "2026-11": METRICS },
};

beforeEach(() => {
    mocked.fetchReviewAgreement.mockReset().mockResolvedValue(REPORT);
});

describe("ReviewAgreementSection", () => {
    it("renders the headline rates, the matrix, and the small-sample warning", async () => {
        render(
            <LanguageProvider>
                <ReviewAgreementSection />
            </LanguageProvider>
        );

        expect(await screen.findByText("AIレビューと教員判定の一致")).toBeInTheDocument();
        expect(screen.getAllByText("60%").length).toBeGreaterThan(0);
        expect(screen.getAllByText("75%").length).toBeGreaterThan(0);
        expect(screen.getAllByText(/件数が少なすぎます\(n=10\)/).length).toBeGreaterThan(0);
        // Grouping with more than one member renders a block per group.
        expect(screen.getByText("r1")).toBeInTheDocument();
        expect(screen.getByText("r2")).toBeInTheDocument();
        // Single-member groups are not repeated below the overall block.
        expect(screen.queryByText("回答プロンプト別")).not.toBeInTheDocument();
    });
});
