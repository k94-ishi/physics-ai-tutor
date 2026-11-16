"""The ask path does not block other requests ([70]).

The rest of the suite proves the ask flow still behaves the same; this
file proves the thing the conversion was for. It needs real concurrency,
so it drives the app through an async client rather than `TestClient`.

Two kinds of test here, and they prove different things:

- The *parked* tests hold a generation open and check that other
  requests are still served meanwhile. Deterministic, no timing
  assertions, so they cannot flake on a loaded machine.
- `test_many_slow_generations_run_at_the_same_time` is the timing one,
  and the only one that actually detects a blocked event loop: replacing
  `asyncio.sleep` with `time.sleep` in the stub makes it fail (checked),
  because 12 generations then take 12x as long instead of 1x.
"""

import asyncio

import pytest
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.api import dependencies
from physics_ai_tutor.database.dependency import get_async_db
from physics_ai_tutor.main import app
from physics_ai_tutor.models import Question
from physics_ai_tutor.schemas.language import TextProvenance
from physics_ai_tutor.schemas.question import QuestionSource, QuestionStatus
from physics_ai_tutor.services import deepseek_service, embedding_service
from tests.conftest import async_engine, fake_generation, reset_database

pytestmark = pytest.mark.anyio

ASK_PATH = "/api/v1/ai/ask"
SEARCH_PATH = "/api/v1/questions/search"
HEALTH_PATH = "/api/v1/db-health"
SLOW_SECONDS = 0.5
CACHED_QUESTION = "キャッシュ済みの質問です"


@pytest.fixture
async def async_client_app():
    """The app over an in-process async transport, on the test database."""
    reset_database()

    async def override_get_async_db():
        async with AsyncSession(async_engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_async_db] = override_get_async_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


async def _seed_cached_answer() -> None:
    """One approved row the ask flow can serve from its tier-0 cache."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        session.add(
            Question(
                question_ja=CACHED_QUESTION,
                answer_ja="キャッシュ済みの回答",
                ja_provenance=TextProvenance.ORIGINAL,
                original_language="ja",
                status=QuestionStatus.APPROVED,
                source=QuestionSource.MANUAL,
            )
        )
        await session.commit()


def _parked_generation(answer: str, started: asyncio.Event, release: asyncio.Event):
    """A generation that reports it began, then waits to be let go."""

    async def _generate(system_prompt, user_prompt, temperature=None, **kwargs):
        started.set()
        await release.wait()
        return fake_generation(answer)(system_prompt, user_prompt)

    return _generate


def _slow_generation(answer: str):
    """A generation that takes SLOW_SECONDS without blocking the loop."""

    async def _generate(system_prompt, user_prompt, temperature=None, **kwargs):
        await asyncio.sleep(SLOW_SECONDS)
        return fake_generation(answer)(system_prompt, user_prompt)

    return _generate


async def test_other_requests_are_served_while_a_generation_is_in_flight(
    async_client_app, monkeypatch
):
    """A pending LLM call does not hold the server ([70]).

    Before the conversion a generation occupied one of the ~40 anyio
    threads for its whole duration, and enough of them stalled every
    other request - [68] measured /health at a 15.6 s p95 under load.
    """
    await _seed_cached_answer()
    started, release = asyncio.Event(), asyncio.Event()
    monkeypatch.setattr(
        deepseek_service,
        "async_generate_answer",
        _parked_generation("遅い回答", started, release),
    )

    slow = asyncio.create_task(
        async_client_app.post(ASK_PATH, json={"question": "遅い生成を伴う質問です"})
    )
    await started.wait()

    # The generation is parked right now, so these are served alongside it.
    health = await async_client_app.get(HEALTH_PATH)
    cached = await async_client_app.post(ASK_PATH, json={"question": CACHED_QUESTION})

    assert health.status_code == 200
    assert cached.status_code == 200
    assert cached.json()["cached"] is True
    assert not slow.done()

    release.set()
    slow_response = await slow

    assert slow_response.status_code == 200
    assert slow_response.json()["answer"] == "遅い回答"


async def test_many_slow_generations_run_at_the_same_time(
    async_client_app, monkeypatch
):
    """Concurrent generations overlap instead of queueing one per thread.

    This is the test that would fail on the pre-[70] code: with a
    blocking call, 12 asks take 12 x SLOW_SECONDS.
    """
    monkeypatch.setattr(
        deepseek_service, "async_generate_answer", _slow_generation("同時回答")
    )
    # Anonymous callers get 3 asks an hour; this test is about the loop,
    # not the limiter, so give it room.
    monkeypatch.setattr(dependencies, "ANONYMOUS_AI_ASK_LIMITS", [(100, 3600)])

    count = 12
    started = asyncio.get_running_loop().time()
    responses = await asyncio.gather(
        *(
            async_client_app.post(
                ASK_PATH, json={"question": f"同時実行の質問 {i} です"}
            )
            for i in range(count)
        )
    )
    elapsed = asyncio.get_running_loop().time() - started

    assert [response.status_code for response in responses] == [200] * count
    # Serial execution would take count * SLOW_SECONDS; overlapping is ~one.
    assert elapsed < SLOW_SECONDS * 3


async def test_search_is_served_alongside_a_pending_embedding_call(
    async_client_app, monkeypatch
):
    """The other converted route: a pending embedding frees the loop too."""
    started, release = asyncio.Event(), asyncio.Event()

    async def _parked_embeddings(texts):
        started.set()
        await release.wait()
        return [[0.1] * 1536 for _ in texts]

    monkeypatch.setattr(
        embedding_service, "async_create_embeddings", _parked_embeddings
    )

    search = asyncio.create_task(
        async_client_app.post(SEARCH_PATH, json={"query": "埋め込みが遅い検索"})
    )
    await started.wait()

    health = await async_client_app.get(HEALTH_PATH)

    assert health.status_code == 200
    assert not search.done()

    release.set()

    assert (await search).status_code == 200
