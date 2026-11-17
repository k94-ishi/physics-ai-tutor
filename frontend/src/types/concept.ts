// Concept senses and their words ([55]).
import { ContentLanguage, QuestionStatus } from "@/types/question";

export type ConceptSearchItem = {
    id: number;
    label: string;
    gloss: string | null;
    matched_term: string | null;
    question_count: number;
};

export type TermSource = "EXTRACTED" | "MACHINE" | "TEACHER";

export type ConceptTerm = {
    id: number;
    language: ContentLanguage;
    term: string;
    is_preferred: boolean;
    source: TermSource;
};

export type AdminConcept = {
    id: number;
    gloss_ja: string | null;
    gloss_en: string | null;
    terms: ConceptTerm[];
    question_count: number;
    shares_word_with: number[];
    questions: { id: number; question: string; status: QuestionStatus }[] | null;
};

export type AdminConceptList = {
    items: AdminConcept[];
    total: number;
    page: number;
    size: number;
};

export type ConceptReviewFilter = "all" | "review" | "shared";
