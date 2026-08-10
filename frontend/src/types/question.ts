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