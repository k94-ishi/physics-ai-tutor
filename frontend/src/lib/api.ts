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