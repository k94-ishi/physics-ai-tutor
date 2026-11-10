import hashlib
import logging
import unicodedata

from openai import OpenAIError
from sqlalchemy.orm import Session

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.exceptions import EmbeddingGenerationError
from physics_ai_tutor.core.openai import client
from physics_ai_tutor.repositories import query_embedding_repository
from physics_ai_tutor.repositories.embedding_repository import (
    search_similar_embeddings,
)
from physics_ai_tutor.schemas.embedding import SimilarQuestionResponse
from physics_ai_tutor.schemas.language import Language

logger = logging.getLogger(__name__)


# Vectors loaded from seed_embeddings.jsonl.gz while seeding, keyed by
# vector_key(model, text); empty otherwise.
_preloaded: dict[str, list[float]] = {}


def vector_key(model: str, text: str) -> str:
    """Stable key of one embedding: the model and the exact text."""
    return hashlib.sha256(f"{model}\0{text}".encode()).hexdigest()


def preload(vectors: dict[str, list[float]]) -> None:
    """Serve these vectors instead of calling OpenAI (seed only)."""
    _preloaded.update(vectors)


def clear_preloaded() -> None:
    _preloaded.clear()


def create_embeddings(texts: list[str]) -> list[list[float]]:
    """Embeddings for `texts`; preloaded vectors first, OpenAI for the rest."""
    keys = [vector_key(settings.embedding_model, text) for text in texts]
    missing = [
        text for text, key in zip(texts, keys, strict=True) if key not in _preloaded
    ]
    fetched = iter(_request_embeddings(missing) if missing else [])
    return [_preloaded[key] if key in _preloaded else next(fetched) for key in keys]


def _request_embeddings(texts: list[str]) -> list[list[float]]:
    logger.debug("Generating embeddings: count=%d", len(texts))

    try:
        response = client.embeddings.create(
            model=settings.embedding_model,
            input=texts,
        )
    except OpenAIError as exc:
        logger.warning("OpenAI embedding generation failed: %s", type(exc).__name__)
        raise EmbeddingGenerationError(
            "Failed to generate embeddings via OpenAI API."
        ) from exc

    logger.info(
        "Generated embeddings: count=%d model=%s", len(texts), settings.embedding_model
    )

    return [item.embedding for item in response.data]


def normalize_query(text: str) -> str:
    """NFKC + whitespace collapse, so trivially different strings share
    one cache entry (and one embedding)."""
    return " ".join(unicodedata.normalize("NFKC", text).split())


def embed_query(db: Session, text: str) -> list[float]:
    """Embed a search query through the cache ([49]).

    Keyed by (hash of the normalised text, model): a repeated search - a
    retried phrasing, a shared ?similar= link, a re-asked question - costs
    no OpenAI call. A model change misses the cache by construction.
    """
    normalized = normalize_query(text)
    text_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    model = settings.embedding_model

    cached = query_embedding_repository.get(db, text_hash, model)
    if cached is not None:
        try:
            query_embedding_repository.touch(db, cached)
        except Exception:
            # Hit bookkeeping must never break a search.
            logger.warning("query embedding touch failed", exc_info=True)
            db.rollback()
        return list(cached.embedding)

    embedding = create_embeddings([normalized])[0]
    row = query_embedding_repository.create(db, text_hash, normalized, model, embedding)

    return list(row.embedding)


def search_similar_questions(
    db: Session,
    query: str,
    limit: int = 10,
    exclude_statuses: list[str] | None = None,
    language: Language | str = Language.JA,
) -> list[SimilarQuestionResponse]:
    lang = Language(language)
    query_embedding = embed_query(db, query)

    # Same-language search only: every row is embedded in each language it
    # has text for, so cross-language scoring is not needed.
    results = search_similar_embeddings(
        db=db,
        embedding=query_embedding,
        embedding_type="question",
        limit=limit,
        exclude_statuses=exclude_statuses,
        language=lang.value,
    )

    logger.info(
        "Similar question search completed: query_length=%d limit=%d results=%d",
        len(query),
        limit,
        len(results),
    )

    responses = []
    for _, question, distance in results:
        text = question.text(lang)
        assert text is not None
        responses.append(
            SimilarQuestionResponse(
                id=question.id,
                question=text[0],
                answer=text[1],
                language=lang,
                distance=distance,
            )
        )

    return responses
