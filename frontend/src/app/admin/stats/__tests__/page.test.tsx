import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AdminStatsResponse } from "@/types/question";

vi.mock("@/lib/api", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@/lib/api")>();
    return { ...actual, fetchAdminStats: vi.fn() };
});

import * as api from "@/lib/api";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";
import AdminStatsPage from "@/app/admin/stats/page";

const mocked = vi.mocked(api);

const STATS: AdminStatsResponse = {
    days: 14,
    daily: [
        {
            day: "2026-10-27",
            generations: 4,
            asks: 6,
            cache_hits: 3,
            distinct_users: 2,
        },
        {
            day: "2026-10-28",
            generations: 1,
            asks: 2,
            cache_hits: 1,
            distinct_users: 1,
        },
    ],
    unreviewed_count: 5,
    unreviewed_median_age_days: 2.4,
    anonymous_ip_buckets_24h: 7,
};

function renderPage() {
    return render(
        <LanguageProvider>
            <AdminStatsPage />
        </LanguageProvider>
    );
}

beforeEach(() => {
    mocked.fetchAdminStats.mockReset().mockResolvedValue(STATS);
});

describe("AdminStatsPage", () => {
    it("shows totals and the per-day table", async () => {
        renderPage();

        expect(await screen.findByText("未レビューの質問")).toBeInTheDocument();
        expect(screen.getByText("5")).toBeInTheDocument();
        expect(screen.getByText("2.4日")).toBeInTheDocument();
        expect(screen.getByText("7")).toBeInTheDocument();

        const rows = screen.getAllByRole("row");
        // Header row + two data rows.
        expect(rows).toHaveLength(3);
        expect(rows[2]).toHaveTextContent("2");
        expect(mocked.fetchAdminStats).toHaveBeenCalledWith(14);
    });

    it("refetches when the window changes", async () => {
        const user = userEvent.setup();
        renderPage();

        await screen.findByText("未レビューの質問");
        await user.selectOptions(screen.getByRole("combobox"), "30");

        expect(mocked.fetchAdminStats).toHaveBeenLastCalledWith(30);
    });

    it("shows an error state with retry", async () => {
        mocked.fetchAdminStats.mockRejectedValue(new Error("boom"));

        renderPage();

        expect(
            await screen.findByText("利用状況を取得できませんでした。")
        ).toBeInTheDocument();
    });
});
