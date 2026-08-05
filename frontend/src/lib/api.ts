import { Question } from "@/types/question";

const API_URL = process.env.NEXT_PUBLIC_API_URL;
const Questions_URL = `${API_URL}/api/v1/questions`;


export async function fetchQuestions() {
    const response = await fetch(
        Questions_URL,
    );

    if (!response.ok) {
        throw new Error("Failed to fetch questions")
    }

    return response.json();
}

export async function fetchQuestion(
    id: number
): Promise<Question> {
    const response = await fetch(
        `${Questions_URL}/${id}`
    );

    if (!response.ok) {
        throw new Error("Failed to fetch questions")
    }

    return response.json();
}

export async function deleteQuestion(
    id: number
): Promise<void> {
    const response = await fetch(
        `${Questions_URL}/${id}`,
        {
            method: "DELETE",
        }
    );

    if (!response.ok) {
        throw new Error("Failed to delete question");
    }
}

export interface CraeteQuestionRequest {
    question: string;
    answer: string;
}

export async function createQuestion(
    data: CraeteQuestionRequest
): Promise<Question> {
    const response = await fetch(
        `${Questions_URL}`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(data),
        }
    );

    if (!response.ok) {
        throw new Error("Failed to create question");
    }

    return response.json();
}
