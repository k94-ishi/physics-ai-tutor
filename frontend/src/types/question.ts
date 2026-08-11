export type Question = {
    id: number;
    question: string;
    answer: string;
};

export type QuestionListResponse = {
    items: Question[];
    total: number;
    page: number;
    size: number;
};

export type CreateQuestionRequest = {
    question: string;
    answer: string;
};

export type UpdateQuestionRequest = {
    id: number;
    question: string;
    answer: string;
};

export type SimilarQuestion = {
    id: number;
    question: string;
    answer: string;
    distance: number;
};

export type FetchQuestionsParams = {
    page?: number;
    size?: number;
    keyword?: string;
};

export type SearchQuestionsParams = {
    query: string;
    limit?: number;
};