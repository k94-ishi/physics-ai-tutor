
QUESTION = "question"
ANSWER = "answer"

def test_create_question(client):
    response = client.post(
        "/api/v1/questions",
        json={
            QUESTION: "テスト質問",
            ANSWER: "テスト回答",
        },
    )
    
    assert response.status_code == 200
    
    data = response.json()
    
    assert data[QUESTION] == "テスト質問"
    assert data[ANSWER] == "テスト回答"
    assert "id" in data