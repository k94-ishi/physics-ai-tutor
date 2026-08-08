from enum import StrEnum
from typing import Literal


PATH = "/api/v1/questions"

class Key(StrEnum):
    QUESTION = "question"
    ANSWER = "answer"
    ID = "id"


def test_create_question(client):
    response = client.post(
        PATH,
        json={
            Key.QUESTION: "テスト質問",
            Key.ANSWER: "テスト回答",
        },
    )
    
    assert response.status_code == 200
    
    data = response.json()
    
    assert data[Key.QUESTION] == "テスト質問"
    assert data[Key.ANSWER] == "テスト回答"
    assert isinstance(data[Key.ID], int)


def test_get_questions(client):
    client.post(
        PATH,
        json={
            Key.QUESTION: "一覧テスト質問",
            Key.ANSWER: "一覧テスト回答",
        },
    )
    
    response = client.get(PATH)
    
    assert response.status_code == 200
    
    data = response.json()
    
    assert len(data) >= 1
    
    question = data[0]
    
    assert question[Key.QUESTION] == "一覧テスト質問"
    assert question[Key.ANSWER] == "一覧テスト回答"


def test_get_question_detail(client):
    create_response = client.post(
        PATH,
        json={
            Key.QUESTION: "詳細テスト質問",
            Key.ANSWER: "詳細テスト回答",
        },
    )
    
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
    create_response = client.post(
        PATH,
        json={
            Key.QUESTION: "更新前質問",
            Key.ANSWER: "更新前回答",
        },
    )
    
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
    create_response = client.post(
        PATH,
        json={
            Key.QUESTION: "削除対象質問",
            Key.ANSWER: "削除対象回答"
        },
    )
    
    question_id = create_response.json()[Key.ID]
    
    response = client.delete(
        f"{PATH}/{question_id}"
    )
    
    assert response.status_code == 204
    
    get_response = client.get(
        f"{PATH}/{question_id}"
    )
    
    assert get_response.status_code == 404