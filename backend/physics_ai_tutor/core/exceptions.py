class EmbeddingGenerationError(Exception):
    """Raised when embedding generation via the OpenAI API fails."""


class ConceptExtractionError(Exception):
    """Raised when concept extraction via the DeepSeek API fails."""


class DeepSeekGenerationError(Exception):
    """Raised when a direct DeepSeek chat completion request fails."""


class DuplicateQuestionError(Exception):
    """Raised when a question with identical text already exists."""
