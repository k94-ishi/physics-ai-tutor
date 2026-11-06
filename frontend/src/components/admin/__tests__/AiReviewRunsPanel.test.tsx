import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AiReviewRun } from "@/types/aiReviewRun";

vi.mock("@/lib/api", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@/lib/api")>();
    return {
        ...actual,
        fetchAiReviewPendingCount: vi.fn(),
        fetchAiReviewRuns: vi.fn(),
        fetchAiReviewRun: vi.fn(),
        startAiReviewRun: vi.fn(),
    };
});

vi.mock("@/components/ui/Toast", () => ({
    showToast: vi.fn(),
    default: () => null,
}));

import * as api from "@/lib/api";
import { showToast } from "@/components/ui/Toast";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";
import AiReviewRunsPanel from "@/components/admin/AiReviewRunsPanel";

const mocked = vi.mocked(api);
const mockedToast = vi.mocked(showToast);

const COUNTS = {
    pending: 3,
    stale: 0,
    daily_cap: 200,
    used_24h: 0,
    remaining: 200,
    would_review_pending: 3,
    would_review_stale: 0,
};

function makeRun(overrides: Partial<AiReviewRun> = {}): AiReviewRun {
    return {
        id: 11,
        trigger: "manual",
        scope: "pending",
        started_by_user_id: 1,
        requested_count: 3,
        reviewed_count: 0,
        skipped_count: 0,
        failed_count: 0,
        prompt_tokens: 0,
        completion_tokens: 0,
        status: "running",
        error: null,
        started_at: "2026-11-01T00:00:00Z",
        finished_at: null,
        ...overrides,
    };
}

async function renderPanel(onRunFinished?: () => void) {
    render(
        <LanguageProvider>
            <AiReviewRunsPanel onRunFinished={onRunFinished} />
        </LanguageProvider>
    );
    await screen.findByText("AIレビュー実行");
}

beforeEach(() => {
    // Fake timers drive the 2.5s polling; shouldAdvanceTime keeps
    // waitFor/findBy (which use real timers) from deadlocking.
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mocked.fetchAiReviewPendingCount.mockReset().mockResolvedValue(COUNTS);
    mocked.fetchAiReviewRuns.mockReset().mockResolvedValue([]);
    mocked.fetchAiReviewRun.mockReset();
    mocked.startAiReviewRun.mockReset();
    mockedToast.mockReset();
});

afterEach(() => {
    vi.useRealTimers();
});

describe("AiReviewRunsPanel", () => {
    it("shows the backlog, confirms with the number of calls, and tracks progress to done", async () => {
        const user = userEvent.setup({
            advanceTimers: (ms) => vi.advanceTimersByTime(ms),
        });
        const onRunFinished = vi.fn();
        await renderPanel(onRunFinished);

        // The dialog must quote the number of DeepSeek calls before starting.
        await user.click(
            screen.getByRole("button", { name: "未判定をすべてAIレビュー" })
        );
        expect(screen.getByText(/DeepSeekを3回呼び出します/)).toBeInTheDocument();

        mocked.startAiReviewRun.mockResolvedValue(makeRun());
        await user.click(screen.getByRole("button", { name: "開始" }));

        expect(mocked.startAiReviewRun).toHaveBeenCalledWith({
            scope: "pending",
            questionIds: undefined,
        });
        await screen.findByText("0 / 3 件処理済み");

        // First poll: two questions processed.
        mocked.fetchAiReviewRun.mockResolvedValueOnce(
            makeRun({ reviewed_count: 2 })
        );
        await vi.advanceTimersByTimeAsync(2500);
        await screen.findByText("2 / 3 件処理済み");

        // Second poll: the run is done; the panel reloads and reports.
        mocked.fetchAiReviewRun.mockResolvedValueOnce(
            makeRun({
                status: "done",
                reviewed_count: 2,
                skipped_count: 1,
                finished_at: "2026-11-01T00:01:00Z",
            })
        );
        await vi.advanceTimersByTimeAsync(2500);

        await waitFor(() => expect(onRunFinished).toHaveBeenCalled());
        expect(mockedToast).toHaveBeenCalledWith(
            "AIレビュー完了: 判定2件、対象外1件、失敗0件"
        );
        expect(screen.queryByText(/件処理済み/)).not.toBeInTheDocument();
        // Counts were requested again after the run.
        expect(mocked.fetchAiReviewPendingCount).toHaveBeenCalledTimes(2);
    });

    it("turns a 409 into a toast instead of starting a second run", async () => {
        const user = userEvent.setup({
            advanceTimers: (ms) => vi.advanceTimersByTime(ms),
        });
        await renderPanel();

        await user.click(
            screen.getByRole("button", { name: "未判定をすべてAIレビュー" })
        );
        mocked.startAiReviewRun.mockRejectedValue(new api.ApiError(409, "busy"));
        await user.click(screen.getByRole("button", { name: "開始" }));

        expect(mockedToast).toHaveBeenCalledWith(
            "別のAIレビューが実行中です。",
            "error"
        );
        expect(screen.queryByText(/件処理済み/)).not.toBeInTheDocument();
    });

    it("adopts a run that is already running and disables the buttons", async () => {
        mocked.fetchAiReviewRuns.mockResolvedValue([
            makeRun({ reviewed_count: 1 }),
        ]);
        await renderPanel();

        await screen.findByText("1 / 3 件処理済み");
        expect(
            screen.getByRole("button", { name: "未判定をすべてAIレビュー" })
        ).toBeDisabled();
        expect(
            screen.getByText("実行中のランが終わるまで開始できません。")
        ).toBeInTheDocument();
    });

    it("explains why nothing can start when the budget is spent", async () => {
        mocked.fetchAiReviewPendingCount.mockResolvedValue({
            ...COUNTS,
            used_24h: 200,
            remaining: 0,
            would_review_pending: 0,
        });
        await renderPanel();

        expect(
            screen.getByRole("button", { name: "未判定をすべてAIレビュー" })
        ).toBeDisabled();
        expect(
            screen.getByText("本日の回数上限に達しています。")
        ).toBeInTheDocument();
    });
});
