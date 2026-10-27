class EmbeddingGenerationError(Exception):
    """Raised when embedding generation via the OpenAI API fails."""


class ConceptExtractionError(Exception):
    """Raised when concept extraction via the DeepSeek API fails."""


class DeepSeekGenerationError(Exception):
    """Raised when a direct DeepSeek chat completion request fails."""


class DuplicateQuestionError(Exception):
    """Raised when a question with identical text already exists."""


class TranslationError(Exception):
    """Raised when translating a question/answer pair fails."""


class RateLimitExceeded(Exception):
    """Raised when a caller has exhausted a sliding-window rate limit."""


class GoogleAuthError(Exception):
    """Raised when the Google OAuth code exchange or ID token is invalid."""


class GoogleAccountConflictError(Exception):
    """Raised when a Google sign-in matches an e-mail owned by a password account."""
