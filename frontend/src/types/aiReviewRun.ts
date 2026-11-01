export type AiReviewRunScope = "pending" | "stale" | "selected";

export type AiReviewRunStatus = "running" | "done" | "failed" | "cancelled";

export type AiReviewRun = {
    id: number;
    trigger: string;
    scope: AiReviewRunScope;
    started_by_user_id: number | null;
    requested_count: number;
    reviewed_count: number;
    skipped_count: number;
    failed_count: number;
    prompt_tokens: number;
    completion_tokens: number;
    status: AiReviewRunStatus;
    error: string | null;
    started_at: string;
    finished_at: string | null;
};

export type AiReviewPendingCount = {
    // True totals, not capped by the daily budget.
    pending: number;
    stale: number;
    daily_cap: number;
    used_24h: number;
    remaining: number;
    // What a run started now would actually touch: min(total, remaining).
    would_review_pending: number;
    would_review_stale: number;
};
