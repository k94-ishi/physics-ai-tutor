// Concept (tag) search and the admin concept editor ([64]).

import {
    AdminConcept,
    AdminConceptList,
    ConceptReviewFilter,
    ConceptSearchItem,
} from "@/types/concept";
import { ContentLanguage } from "@/types/question";
import {
    apiFetch,
    getAdminConceptsUrl,
    getConceptsUrl,
    jsonInit,
} from "@/lib/api/client";

export async function searchConcepts(
    q: string,
    lang: ContentLanguage,
    limit = 20,
): Promise<ConceptSearchItem[]> {
    const params = new URLSearchParams({ q, lang, limit: String(limit) });
    return apiFetch<ConceptSearchItem[]>(`${getConceptsUrl()}?${params}`);
}

export async function fetchAdminConcepts(params: {
    q?: string;
    filter?: ConceptReviewFilter;
    page?: number;
    size?: number;
}): Promise<AdminConceptList> {
    const search = new URLSearchParams({
        q: params.q ?? "",
        review_filter: params.filter ?? "all",
        page: String(params.page ?? 1),
        size: String(params.size ?? 30),
    });
    return apiFetch<AdminConceptList>(`${getAdminConceptsUrl()}?${search}`);
}

export async function fetchAdminConcept(
    id: number,
    lang: ContentLanguage,
): Promise<AdminConcept> {
    return apiFetch<AdminConcept>(
        `${getAdminConceptsUrl()}/${id}?lang=${lang}`,
    );
}

export async function updateConceptGloss(
    id: number,
    gloss: { gloss_ja: string | null; gloss_en: string | null },
    lang: ContentLanguage,
): Promise<AdminConcept> {
    return apiFetch<AdminConcept>(
        `${getAdminConceptsUrl()}/${id}?lang=${lang}`,
        jsonInit("PATCH", gloss),
    );
}

export async function addConceptTerm(
    id: number,
    term: { language: ContentLanguage; term: string; is_preferred: boolean },
    lang: ContentLanguage,
): Promise<AdminConcept> {
    return apiFetch<AdminConcept>(
        `${getAdminConceptsUrl()}/${id}/terms?lang=${lang}`,
        jsonInit("POST", term),
    );
}

export async function updateConceptTerm(
    termId: number,
    change: { term?: string; is_preferred?: boolean },
    lang: ContentLanguage,
): Promise<AdminConcept> {
    return apiFetch<AdminConcept>(
        `${getAdminConceptsUrl()}/terms/${termId}?lang=${lang}`,
        jsonInit("PATCH", change),
    );
}

export async function deleteConceptTerm(termId: number): Promise<void> {
    return apiFetch<void>(`${getAdminConceptsUrl()}/terms/${termId}`, {
        method: "DELETE",
    });
}

export async function mergeConcept(
    id: number,
    intoId: number,
    lang: ContentLanguage,
): Promise<AdminConcept> {
    return apiFetch<AdminConcept>(
        `${getAdminConceptsUrl()}/${id}/merge?lang=${lang}`,
        jsonInit("POST", { into_id: intoId }),
    );
}

export async function splitConcept(
    id: number,
    body: {
        question_ids: number[];
        terms: { language: ContentLanguage; term: string }[];
        gloss_ja?: string;
        gloss_en?: string;
    },
    lang: ContentLanguage,
): Promise<AdminConcept> {
    return apiFetch<AdminConcept>(
        `${getAdminConceptsUrl()}/${id}/split?lang=${lang}`,
        jsonInit("POST", body),
    );
}
