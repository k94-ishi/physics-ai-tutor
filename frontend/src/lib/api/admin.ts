// Admin dashboards and AI review runs ([64]).

import {
    AiReviewPendingCount,
    AiReviewRun,
    AiReviewRunScope,
} from "@/types/aiReviewRun";
import { AdminStatsResponse, ReviewAgreementResponse } from "@/types/question";
import { apiFetch, getApiUrl } from "@/lib/api/client";

export async function fetchReviewAgreement(): Promise<ReviewAgreementResponse> {
    return apiFetch<ReviewAgreementResponse>(
        `${getApiUrl()}/api/v1/admin/stats/review-agreement`,
    );
}

export async function fetchAdminStats(
    days: number,
): Promise<AdminStatsResponse> {
    return apiFetch<AdminStatsResponse>(
        `${getApiUrl()}/api/v1/admin/stats?days=${days}`,
    );
}

export async function fetchAiReviewPendingCount(): Promise<AiReviewPendingCount> {
    return apiFetch<AiReviewPendingCount>(
        `${getApiUrl()}/api/v1/admin/ai-review/pending-count`,
    );
}

export async function fetchAiReviewRuns(limit = 10): Promise<AiReviewRun[]> {
    return apiFetch<AiReviewRun[]>(
        `${getApiUrl()}/api/v1/admin/ai-review/runs?limit=${limit}`,
    );
}

export async function fetchAiReviewRun(id: number): Promise<AiReviewRun> {
    return apiFetch<AiReviewRun>(
        `${getApiUrl()}/api/v1/admin/ai-review/runs/${id}`,
    );
}

export async function startAiReviewRun(params: {
    scope: AiReviewRunScope;
    questionIds?: number[];
}): Promise<AiReviewRun> {
    return apiFetch<AiReviewRun>(`${getApiUrl()}/api/v1/admin/ai-review/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            scope: params.scope,
            question_ids: params.questionIds,
        }),
    });
}
