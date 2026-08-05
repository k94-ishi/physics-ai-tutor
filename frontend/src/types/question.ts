export type Question = {
    id: number;
    question: string;
    answer: string;
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