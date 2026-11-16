import hashlib
import logging

from openai import OpenAIError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.core import timing
from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.exceptions import EmbeddingGenerationError
from physics_ai_tutor.core.openai import async_client
from physics_ai_tutor.core.text import normalize_text
from physics_ai_tutor.database.transaction import async_transaction
from physics_ai_tutor.repositories import query_embedding_repository
from physics_ai_tutor.repositories.embedding_repository import (
    async_search_similar_embeddings,
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


# One OpenAI request per chunk ([76]). The API allows 2048 inputs and a
# few hundred thousand tokens per request; these stay well inside both,
# since a long answer plus its question can run to a few thousand chars.
EMBED_BATCH_MAX_ITEMS = 256
EMBED_BATCH_MAX_CHARS = 200_000


def _chunks(texts: list[str]) -> list[list[str]]:
    """Split by count and by total length, keeping the order."""
    chunks: list[list[str]] = []
    current: list[str] = []
    size = 0
    for text in texts:
        if current and (
            len(current) >= EMBED_BATCH_MAX_ITEMS
            or size + len(text) > EMBED_BATCH_MAX_CHARS
        ):
            chunks.append(current)
            current, size = [], 0
        current.append(text)
        size += len(text)
    if current:
        chunks.append(current)
    return chunks


async def async_embed_many(texts: list[str]) -> list[list[float]]:
    """Embeddings for many texts, one request per chunk, in input order ([76]).

    `async_create_embeddings` is called per chunk, so preloaded seed
    vectors and the test seam apply unchanged. The result lines up with
    `texts` by index; callers keep their own (row, language, kind) mapping.
    """
    vectors: list[list[float]] = []
    for chunk in _chunks(texts):
        vectors.extend(await async_create_embeddings(chunk))
    assert len(vectors) == len(texts)
    return vectors


def _similar_responses(
    results, lang: Language, query_length: int, limit: int
) -> list[SimilarQuestionResponse]:
    """Shape search rows into responses."""
    logger.info(
        "Similar question search completed: query_length=%d limit=%d results=%d",
        query_length,
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


async def async_create_embeddings(texts: list[str]) -> list[list[float]]:
    """Embeddings for `texts`; preloaded vectors first, OpenAI for the rest."""
    keys = [vector_key(settings.embedding_model, text) for text in texts]
    missing = [
        text for text, key in zip(texts, keys, strict=True) if key not in _preloaded
    ]
    fetched = iter(await _async_request_embeddings(missing) if missing else [])
    return [_preloaded[key] if key in _preloaded else next(fetched) for key in keys]


async def _async_request_embeddings(texts: list[str]) -> list[list[float]]:
    logger.debug("Generating embeddings: count=%d", len(texts))

    try:
        with timing.stage("openai_embeddings", count=len(texts)):
            response = await async_client.embeddings.create(
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


async def async_embed_query(db: AsyncSession, text: str) -> list[float]:
    """Embed a search query through the cache ([49]).

    Keyed by (hash of the normalised text, model): a repeated search - a
    retried phrasing, a shared ?similar= link, a re-asked question - costs
    no OpenAI call. A model change misses the cache by construction.
    """
    normalized = normalize_text(text)
    text_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    model = settings.embedding_model

    with timing.stage("embed_query") as stage:
        # The lookup commits so the connection is back in the pool before
        # the OpenAI call a miss triggers ([82]).
        async with async_transaction(db, "query_embedding_lookup"):
            cached = await query_embedding_repository.async_get(db, text_hash, model)

        if cached is not None:
            stage.note(cache="hit")
            try:
                async with async_transaction(db, "touch_query_embedding"):
                    await query_embedding_repository.async_touch(db, cached)
            except Exception:
                # Hit bookkeeping must never break a search.
                logger.warning("query embedding touch failed", exc_info=True)
            return list(cached.embedding)

        stage.note(cache="miss")
        embedding = (await async_create_embeddings([normalized]))[0]

    try:
        async with async_transaction(db, "cache_query_embedding"):
            row = await query_embedding_repository.async_create(
                db, text_hash, normalized, model, embedding
            )
    except IntegrityError:
        # Two identical searches raced; the other one won and that is fine.
        existing = await query_embedding_repository.async_get(db, text_hash, model)
        assert existing is not None
        return list(existing.embedding)

    return list(row.embedding)


async def async_search_similar_questions(
    db: AsyncSession,
    query: str,
    limit: int = 10,
    exclude_statuses: list[str] | None = None,
    language: Language | str = Language.JA,
) -> list[SimilarQuestionResponse]:
    """Questions whose embedding in `language` is closest to the query."""
    lang = Language(language)
    query_embedding = await async_embed_query(db, query)

    # Same-language search only: every row is embedded in each language it
    # has text for, so cross-language scoring is not needed.
    with timing.stage("vector_search", limit=limit) as stage:
        results = await async_search_similar_embeddings(
            db=db,
            embedding=query_embedding,
            embedding_type="question",
            limit=limit,
            exclude_statuses=exclude_statuses,
            language=lang.value,
        )
        stage.note(results=len(results))

    return _similar_responses(results, lang, len(query), limit)
