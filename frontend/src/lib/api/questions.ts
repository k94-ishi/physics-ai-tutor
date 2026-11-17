// Question endpoints: lists, detail, search, edit, review, import ([64]).

import {
    BulkDeleteResponse,
    BulkReviewAction,
    BulkReviewResponse,
    ConceptExtractionBatchResponse,
    ContentLanguage,
    CreateQuestionRequest,
    FetchQuestionsParams,
    PrerequisitesResponse,
    Question,
    QuestionImportResponse,
    QuestionListResponse,
    QuestionReview,
    QuestionSource,
    QuestionStatus,
    ReviewQuestionRequest,
    ReviewReason,
    SearchQuestionsParams,
    SimilarQuestion,
    TranslationBatchResponse,
    UpdateQuestionRequest,
} from "@/types/question";
import { apiFetch, getQuestionsUrl } from "@/lib/api/client";

export async function fetchQuestions(
    params: FetchQuestionsParams = {},
): Promise<QuestionListResponse> {
    const searchParams = new URLSearchParams();

    if (params.page !== undefined) {
        searchParams.set("page", String(params.page));
    }
    if (params.size !== undefined) {
        searchParams.set("size", String(params.size));
    }
    if (params.keyword) {
        searchParams.set("keyword", params.keyword);
    }
    if (params.sort) {
        searchParams.set("sort", params.sort);
    }
    if (params.aiVerdict) {
        searchParams.set("ai_verdict", params.aiVerdict);
    }
    if (params.status) {
        searchParams.set("status", params.status);
    }
    if (params.searchQuestion !== undefined) {
        searchParams.set("search_question", String(params.searchQuestion));
    }
    if (params.searchAnswer !== undefined) {
        searchParams.set("search_answer", String(params.searchAnswer));
    }
    if (params.lang) {
        searchParams.set("lang", params.lang);
    }
    if (params.ids?.length) {
        searchParams.set("ids", params.ids.join(","));
    }
    if (params.concept) {
        searchParams.set("concept", params.concept);
    }
    if (params.conceptId !== undefined) {
        searchParams.set("concept_id", String(params.conceptId));
    }

    const query = searchParams.toString();

    return apiFetch<QuestionListResponse>(
        query ? `${getQuestionsUrl()}?${query}` : getQuestionsUrl(),
    );
}

export async function searchQuestions(
    params: SearchQuestionsParams,
): Promise<SimilarQuestion[]> {
    return apiFetch<SimilarQuestion[]>(`${getQuestionsUrl()}/search`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(params),
    });
}

export async function fetchQuestion(
    id: number,
    lang?: ContentLanguage,
): Promise<Question> {
    const query = lang ? `?${new URLSearchParams({ lang })}` : "";
    return apiFetch<Question>(`${getQuestionsUrl()}/${id}${query}`);
}

export async function fetchQuestionByExactText(
    question: string,
    lang?: ContentLanguage,
): Promise<Question> {
    const query = new URLSearchParams(
        lang ? { question, lang } : { question },
    ).toString();
    return apiFetch<Question>(`${getQuestionsUrl()}/exact-match?${query}`);
}

export async function deleteQuestion(id: number): Promise<void> {
    return apiFetch<void>(`${getQuestionsUrl()}/${id}`, {
        method: "DELETE",
    });
}

export async function createQuestion(
    data: CreateQuestionRequest,
): Promise<Question> {
    return apiFetch<Question>(getQuestionsUrl(), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    });
}

export async function updateQuestion(
    data: UpdateQuestionRequest,
): Promise<Question> {
    return apiFetch<Question>(`${getQuestionsUrl()}/${data.id}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    });
}

export async function fetchRelatedQuestions(
    id: number,
    limit = 5,
    lang?: ContentLanguage,
): Promise<Question[]> {
    const langParam = lang ? `&lang=${lang}` : "";
    return apiFetch<Question[]>(
        `${getQuestionsUrl()}/${id}/related?limit=${limit}${langParam}`,
    );
}

export async function fetchPrerequisites(
    id: number,
    lang?: ContentLanguage,
): Promise<PrerequisitesResponse> {
    const langParam = lang ? `?lang=${lang}` : "";
    return apiFetch<PrerequisitesResponse>(
        `${getQuestionsUrl()}/${id}/prerequisites${langParam}`,
    );
}

export async function translateQuestions(
    questionIds: number[],
): Promise<TranslationBatchResponse> {
    return apiFetch<TranslationBatchResponse>(
        `${getQuestionsUrl()}/translate`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ question_ids: questionIds }),
        },
    );
}

export async function reviewQuestion(
    id: number,
    data: ReviewQuestionRequest,
): Promise<Question> {
    return apiFetch<Question>(`${getQuestionsUrl()}/${id}/review`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    });
}

export async function fetchQuestionReviews(
    id: number,
): Promise<QuestionReview[]> {
    return apiFetch<QuestionReview[]>(`${getQuestionsUrl()}/${id}/reviews`);
}

export async function importQuestions(
    file: File,
    source: QuestionSource,
    status: QuestionStatus,
): Promise<QuestionImportResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("source", source);
    formData.append("status", status);

    return apiFetch<QuestionImportResponse>(`${getQuestionsUrl()}/import`, {
        method: "POST",
        body: formData,
    });
}

export async function bulkDeleteQuestions(
    questionIds: number[],
): Promise<BulkDeleteResponse> {
    return apiFetch<BulkDeleteResponse>(`${getQuestionsUrl()}/bulk-delete`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ question_ids: questionIds }),
    });
}

export async function bulkReviewQuestions(
    questionIds: number[],
    action: BulkReviewAction,
    reason?: ReviewReason,
    comment?: string,
): Promise<BulkReviewResponse> {
    return apiFetch<BulkReviewResponse>(`${getQuestionsUrl()}/bulk-review`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            question_ids: questionIds,
            action,
            reason,
            comment,
        }),
    });
}

export async function extractConcepts(
    questionIds: number[],
): Promise<ConceptExtractionBatchResponse> {
    return apiFetch<ConceptExtractionBatchResponse>(
        `${getQuestionsUrl()}/concepts/extract`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ question_ids: questionIds }),
        },
    );
}
