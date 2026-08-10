from enum import StrEnum

from physics_ai_tutor.core.exceptions import EmbeddingGenerationError
from physics_ai_tutor.models import QuestionEmbedding
from physics_ai_tutor.services import embedding_service

PATH = "/api/v1/questions"
BULK_PATH = f"{PATH}/bulk"
SEARCH_PATH = f"{PATH}/search"

class Key(StrEnum):
    QUESTION = "question"
    ANSWER = "answer"
    ID = "id"
    QUESTIONS = "questions"
    DISTANCE = "distance"


def _post(client, question: str, answer: str):
    return client.post(
        PATH,
        json={
            Key.QUESTION: question,
            Key.ANSWER: answer,
        },
    )


def _post_bulk(client, items: list[tuple[str, str]]):
    return client.post(
        BULK_PATH,
        json={
            Key.QUESTIONS: [
                {Key.QUESTION: question, Key.ANSWER: answer}
                for question, answer in items
            ],
        },
    )


def test_create_question(client):
    response = _post(client, "テスト質問", "テスト回答")
    
    assert response.status_code == 200
    
    data = response.json()
    
    assert data[Key.QUESTION] == "テスト質問"
    assert data[Key.ANSWER] == "テスト回答"
    assert isinstance(data[Key.ID], int)


def test_get_questions(client):
    _post(client, "一覧テスト質問", "一覧テスト回答")
    
    response = client.get(PATH)
    
    assert response.status_code == 200
    
    data = response.json()
    
    assert len(data) >= 1
    
    question = data[0]
    
    assert question[Key.QUESTION] == "一覧テスト質問"
    assert question[Key.ANSWER] == "一覧テスト回答"


def test_get_question_detail(client):
    create_response = _post(client, "詳細テスト質問", "詳細テスト回答")
    
    assert create_response.status_code == 200
    
    question_id = create_response.json()[Key.ID]
    
    response = client.get(f"{PATH}/{question_id}")
    
    assert response.status_code == 200
    
    data = response.json()
    
    assert data[Key.ID] == question_id
    assert data[Key.QUESTION] == "詳細テスト質問"
    assert data[Key.ANSWER] == "詳細テスト回答"


def test_get_question_not_found(client):
    response = client.get(
        f"{PATH}/99999",
    )
    
    assert response.status_code == 404


def test_update_question(client):
    create_response = _post(client, "更新前質問", "更新前回答")
    
    question_id = create_response.json()["id"]
    
    response = client.put(
        f"{PATH}/{question_id}",
        json={
            Key.QUESTION: "更新後質問",
            Key.ANSWER: "更新後回答",
        },
    )
    
    assert response.status_code == 200
    
    data = response.json()
    
    assert data[Key.QUESTION] == "更新後質問"
    assert data[Key.ANSWER] == "更新後回答"


def test_delete_question(client):
    create_response = _post(client, "削除対象質問", "削除対象回答")
    
    question_id = create_response.json()[Key.ID]
    
    response = client.delete(
        f"{PATH}/{question_id}"
    )
    
    assert response.status_code == 204
    
    get_response = client.get(
        f"{PATH}/{question_id}"
    )

    assert get_response.status_code == 404


def test_create_questions_bulk(client):
    response = _post_bulk(
        client,
        [
            ("一括質問1", "一括回答1"),
            ("一括質問2", "一括回答2"),
        ],
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert data[0][Key.QUESTION] == "一括質問1"
    assert data[0][Key.ANSWER] == "一括回答1"
    assert data[1][Key.QUESTION] == "一括質問2"
    assert data[1][Key.ANSWER] == "一括回答2"


def test_create_questions_bulk_empty(client):
    response = _post_bulk(client, [])

    assert response.status_code == 200
    assert response.json() == []


def test_update_question_not_found(client):
    response = client.put(
        f"{PATH}/99999",
        json={
            Key.QUESTION: "更新後質問",
            Key.ANSWER: "更新後回答",
        },
    )

    assert response.status_code == 404


def test_delete_question_not_found(client):
    response = client.delete(f"{PATH}/99999")

    assert response.status_code == 404


def test_search_questions(client):
    create_response = _post(client, "検索対象質問", "検索対象回答")

    assert create_response.status_code == 200

    question_id = create_response.json()[Key.ID]

    response = client.post(
        SEARCH_PATH,
        json={"query": "検索対象質問に似た質問"},
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1

    result = next(item for item in data if item[Key.ID] == question_id)

    assert result[Key.QUESTION] == "検索対象質問"
    assert result[Key.ANSWER] == "検索対象回答"
    assert isinstance(result[Key.DISTANCE], float)


def test_create_question_embedding_failure_returns_503(client, monkeypatch):
    def _raise(texts):
        raise EmbeddingGenerationError("boom")

    monkeypatch.setattr(embedding_service, "create_embeddings", _raise)

    response = _post(client, "質問", "回答")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Embedding generation failed. Please try again later."
    }

    list_response = client.get(PATH)

    assert list_response.json() == []


def test_search_questions_embedding_failure_returns_503(client, monkeypatch):
    def _raise(texts):
        raise EmbeddingGenerationError("boom")

    monkeypatch.setattr(embedding_service, "create_embeddings", _raise)

    response = client.post(SEARCH_PATH, json={"query": "質問"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Embedding generation failed. Please try again later."
    }


def test_update_question_embedding_failure_returns_503(client, monkeypatch):
    create_response = _post(client, "更新前質問", "更新前回答")
    question_id = create_response.json()[Key.ID]

    def _raise(texts):
        raise EmbeddingGenerationError("boom")

    monkeypatch.setattr(embedding_service, "create_embeddings", _raise)

    response = client.put(
        f"{PATH}/{question_id}",
        json={
            Key.QUESTION: "更新後質問",
            Key.ANSWER: "更新後回答",
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Embedding generation failed. Please try again later."
    }

    get_response = client.get(f"{PATH}/{question_id}")

    assert get_response.json()[Key.QUESTION] == "更新前質問"
    assert get_response.json()[Key.ANSWER] == "更新前回答"


def test_create_questions_bulk_embedding_failure_returns_503(client, monkeypatch):
    def _raise(texts):
        raise EmbeddingGenerationError("boom")

    monkeypatch.setattr(embedding_service, "create_embeddings", _raise)

    response = _post_bulk(client, [("一括質問1", "一括回答1")])

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Embedding generation failed. Please try again later."
    }

    list_response = client.get(PATH)

    assert list_response.json() == []


def test_delete_question_removes_embeddings(client, db):
    create_response = _post(client, "削除対象質問", "削除対象回答")
    question_id = create_response.json()[Key.ID]

    response = client.delete(f"{PATH}/{question_id}")

    assert response.status_code == 204

    remaining = (
        db.query(QuestionEmbedding)
        .filter(QuestionEmbedding.question_id == question_id)
        .all()
    )

    assert remaining == []