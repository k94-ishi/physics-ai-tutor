import json
from enum import StrEnum

from physics_ai_tutor.core.exceptions import EmbeddingGenerationError
from physics_ai_tutor.models import QuestionEmbedding
from physics_ai_tutor.repositories import question_repository
from physics_ai_tutor.services import embedding_service

PATH = "/api/v1/questions"
IMPORT_PATH = f"{PATH}/import"
SEARCH_PATH = f"{PATH}/search"

class Key(StrEnum):
    QUESTION = "question"
    ANSWER = "answer"
    ID = "id"
    QUESTIONS = "questions"
    DISTANCE = "distance"
    STATUS = "status"
    SOURCE = "source"


def _post(client, question: str, answer: str):
    return client.post(
        PATH,
        json={
            Key.QUESTION: question,
            Key.ANSWER: answer,
        },
    )


def _post_import(client, items: list[tuple[str, str]], source=None, status=None):
    content = "\n".join(
        json.dumps({Key.QUESTION: question, Key.ANSWER: answer}, ensure_ascii=False)
        for question, answer in items
    )

    data = {}
    if source is not None:
        data["source"] = source
    if status is not None:
        data["status"] = status

    files = {"file": ("questions.jsonl", content, "application/jsonl")}

    return client.post(IMPORT_PATH, data=data, files=files)


def test_create_question(admin_client):
    response = _post(admin_client, "テスト質問", "テスト回答")

    assert response.status_code == 201

    data = response.json()

    assert data[Key.QUESTION] == "テスト質問"
    assert data[Key.ANSWER] == "テスト回答"
    assert data[Key.STATUS] == "APPROVED"
    assert data[Key.SOURCE] == "MANUAL"
    assert isinstance(data[Key.ID], int)


def test_create_question_requires_admin(client):
    response = _post(client, "テスト質問", "テスト回答")

    assert response.status_code == 401


def test_create_question_forbidden_for_non_admin(user_client):
    response = _post(user_client, "テスト質問", "テスト回答")

    assert response.status_code == 403


def test_create_question_empty_question_rejected(admin_client):
    response = _post(admin_client, "", "テスト回答")

    assert response.status_code == 422


def test_create_question_blank_question_rejected(admin_client):
    response = _post(admin_client, "   ", "テスト回答")

    assert response.status_code == 422


def test_create_question_empty_answer_rejected(admin_client):
    response = _post(admin_client, "テスト質問", "")

    assert response.status_code == 422


def test_create_question_too_long_question_rejected(admin_client):
    response = _post(admin_client, "あ" * 1001, "テスト回答")

    assert response.status_code == 422


def test_create_question_duplicate_rejected(admin_client):
    _post(admin_client, "重複質問", "重複回答1")

    response = _post(admin_client, "重複質問", "重複回答2")

    assert response.status_code == 409


def test_search_questions_empty_query_rejected(client):
    response = client.post(SEARCH_PATH, json={"query": ""})

    assert response.status_code == 422


def test_search_questions_invalid_limit_rejected(client):
    response_zero = client.post(SEARCH_PATH, json={"query": "質問", "limit": 0})
    response_over = client.post(SEARCH_PATH, json={"query": "質問", "limit": 51})

    assert response_zero.status_code == 422
    assert response_over.status_code == 422


def test_get_questions(admin_client):
    _post(admin_client, "一覧テスト質問", "一覧テスト回答")

    response = admin_client.get(PATH)

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1
    assert len(data["items"]) >= 1

    question = data["items"][0]

    assert question[Key.QUESTION] == "一覧テスト質問"
    assert question[Key.ANSWER] == "一覧テスト回答"


def test_get_questions_filters_by_keyword(admin_client):
    _post(admin_client, "運動量保存則とは何ですか", "運動量は保存されます")
    _post(admin_client, "エネルギー保存則とは何ですか", "エネルギーは保存されます")

    response = admin_client.get(PATH, params={"keyword": "運動量"})

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0][Key.QUESTION] == "運動量保存則とは何ですか"


def test_get_questions_invalid_size_rejected(client):
    assert client.get(PATH, params={"size": 0}).status_code == 422
    assert client.get(PATH, params={"size": 121}).status_code == 422


def test_get_questions_invalid_page_rejected(client):
    response = client.get(PATH, params={"page": 0})

    assert response.status_code == 422


def test_get_questions_hides_rejected_from_non_admin(admin_client, client):
    create_response = _post(admin_client, "却下予定質問", "却下予定回答")
    question_id = create_response.json()[Key.ID]

    admin_client.post(f"{PATH}/{question_id}/review", json={"action": "REJECT"})

    admin_list = admin_client.get(PATH, params={"size": 100})
    public_list = client.get(PATH, params={"size": 100})

    admin_ids = [item[Key.ID] for item in admin_list.json()["items"]]
    public_ids = [item[Key.ID] for item in public_list.json()["items"]]

    assert question_id in admin_ids
    assert question_id not in public_ids


def test_get_question_detail(admin_client):
    create_response = _post(admin_client, "詳細テスト質問", "詳細テスト回答")

    assert create_response.status_code == 201

    question_id = create_response.json()[Key.ID]

    response = admin_client.get(f"{PATH}/{question_id}")

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


def test_get_question_rejected_not_found_for_non_admin(admin_client, client):
    create_response = _post(admin_client, "却下予定質問2", "却下予定回答2")
    question_id = create_response.json()[Key.ID]

    admin_client.post(f"{PATH}/{question_id}/review", json={"action": "REJECT"})

    response = client.get(f"{PATH}/{question_id}")

    assert response.status_code == 404


def test_get_exact_match_question_found(admin_client, client):
    create_response = _post(admin_client, "完全一致テスト質問", "完全一致テスト回答")
    question_id = create_response.json()[Key.ID]

    response = client.get(
        f"{PATH}/exact-match", params={"question": "完全一致テスト質問"}
    )

    assert response.status_code == 200
    assert response.json()[Key.ID] == question_id


def test_get_exact_match_question_not_found(client):
    response = client.get(
        f"{PATH}/exact-match", params={"question": "存在しない完全一致質問"}
    )

    assert response.status_code == 404


def test_get_exact_match_question_includes_unreviewed(admin_client, client):
    import_response = _post_import(
        admin_client,
        [("未レビュー完全一致質問", "回答")],
        status="UNREVIEWED",
    )
    question_id = import_response.json()[Key.QUESTIONS][0][Key.ID]

    response = client.get(
        f"{PATH}/exact-match", params={"question": "未レビュー完全一致質問"}
    )

    assert response.status_code == 200
    assert response.json()[Key.ID] == question_id
    assert response.json()[Key.STATUS] == "UNREVIEWED"


def test_get_exact_match_question_excludes_rejected(admin_client, client):
    create_response = _post(admin_client, "却下済み完全一致質問", "回答")
    question_id = create_response.json()[Key.ID]
    admin_client.post(f"{PATH}/{question_id}/review", json={"action": "REJECT"})

    response = client.get(
        f"{PATH}/exact-match", params={"question": "却下済み完全一致質問"}
    )

    assert response.status_code == 404


def test_update_question(admin_client):
    create_response = _post(admin_client, "更新前質問", "更新前回答")

    question_id = create_response.json()["id"]

    response = admin_client.put(
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


def test_update_question_requires_admin(client):
    response = client.put(
        f"{PATH}/99999",
        json={
            Key.QUESTION: "更新後質問",
            Key.ANSWER: "更新後回答",
        },
    )

    assert response.status_code == 401


def test_delete_question(admin_client):
    create_response = _post(admin_client, "削除対象質問", "削除対象回答")

    question_id = create_response.json()[Key.ID]

    response = admin_client.delete(
        f"{PATH}/{question_id}"
    )

    assert response.status_code == 204

    get_response = admin_client.get(
        f"{PATH}/{question_id}"
    )

    assert get_response.status_code == 404


def test_delete_question_requires_admin(client):
    response = client.delete(f"{PATH}/99999")

    assert response.status_code == 401


def test_import_questions(admin_client):
    response = _post_import(
        admin_client,
        [
            ("一括質問1", "一括回答1"),
            ("一括質問2", "一括回答2"),
        ],
    )

    assert response.status_code == 201

    data = response.json()

    assert data["created_count"] == 2
    assert data["questions"][0][Key.QUESTION] == "一括質問1"
    assert data["questions"][0][Key.STATUS] == "UNREVIEWED"
    assert data["questions"][0][Key.SOURCE] == "AI_GENERATED"


def test_import_questions_custom_source_and_status(admin_client):
    response = _post_import(
        admin_client,
        [("手動質問", "手動回答")],
        source="MANUAL",
        status="APPROVED",
    )

    assert response.status_code == 201

    data = response.json()["questions"][0]

    assert data[Key.SOURCE] == "MANUAL"
    assert data[Key.STATUS] == "APPROVED"


def test_import_questions_requires_admin(client):
    response = _post_import(client, [("質問", "回答")])

    assert response.status_code == 401


def test_import_questions_forbidden_for_non_admin(user_client):
    response = _post_import(user_client, [("質問", "回答")])

    assert response.status_code == 403


def test_import_questions_empty_file_rejected(admin_client):
    response = _post_import(admin_client, [])

    assert response.status_code == 422


def test_import_questions_invalid_json_line_rejected(admin_client):
    files = {"file": ("questions.jsonl", "not valid json", "application/jsonl")}

    response = admin_client.post(IMPORT_PATH, files=files)

    assert response.status_code == 422


def test_import_questions_duplicate_within_file_rejected(admin_client):
    response = _post_import(
        admin_client,
        [
            ("重複質問", "回答1"),
            ("重複質問", "回答2"),
        ],
    )

    assert response.status_code == 409

    list_response = admin_client.get(PATH, params={"size": 100})
    assert list_response.json()["total"] == 0


def test_import_questions_duplicate_against_existing_rejected(admin_client):
    _post(admin_client, "既存質問", "既存回答")

    response = _post_import(admin_client, [("既存質問", "新規回答")])

    assert response.status_code == 409


def test_create_questions_bulk_route_removed(admin_client):
    response = admin_client.post(
        f"{PATH}/bulk",
        json={"questions": [{"question": "質問", "answer": "回答"}]},
    )

    # "/questions/bulk" now matches the "/questions/{question_id}" path
    # template (which only supports GET/PUT/DELETE), so POST there is a
    # correct 405, not a 404 - the old /bulk endpoint itself no longer exists.
    assert response.status_code == 405


def test_review_question_approve(admin_client):
    create_response = _post_import(admin_client, [("レビュー対象", "レビュー回答")])
    question_id = create_response.json()["questions"][0][Key.ID]

    response = admin_client.post(
        f"{PATH}/{question_id}/review", json={"action": "APPROVE"}
    )

    assert response.status_code == 200
    assert response.json()[Key.STATUS] == "APPROVED"


def test_review_question_reject(admin_client):
    create_response = _post(admin_client, "却下対象", "却下対象回答")
    question_id = create_response.json()[Key.ID]

    response = admin_client.post(
        f"{PATH}/{question_id}/review", json={"action": "REJECT"}
    )

    assert response.status_code == 200
    assert response.json()[Key.STATUS] == "REJECTED"


def test_review_question_edit_approve(admin_client):
    create_response = _post_import(admin_client, [("編集前質問", "編集前回答")])
    question_id = create_response.json()["questions"][0][Key.ID]

    response = admin_client.post(
        f"{PATH}/{question_id}/review",
        json={
            "action": "EDIT_APPROVE",
            "question": "編集後質問",
            "answer": "編集後回答",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data[Key.STATUS] == "APPROVED"
    assert data[Key.QUESTION] == "編集後質問"
    assert data[Key.ANSWER] == "編集後回答"


def test_review_question_edit_approve_requires_content(admin_client):
    create_response = _post(admin_client, "質問", "回答")
    question_id = create_response.json()[Key.ID]

    response = admin_client.post(
        f"{PATH}/{question_id}/review", json={"action": "EDIT_APPROVE"}
    )

    assert response.status_code == 422


def test_review_question_requires_admin(client):
    response = client.post(f"{PATH}/99999/review", json={"action": "APPROVE"})

    assert response.status_code == 401


def test_review_question_not_found(admin_client):
    response = admin_client.post(
        f"{PATH}/99999/review", json={"action": "APPROVE"}
    )

    assert response.status_code == 404


def test_get_question_reviews(admin_client):
    create_response = _post(admin_client, "履歴対象", "履歴対象回答")
    question_id = create_response.json()[Key.ID]

    admin_client.post(f"{PATH}/{question_id}/review", json={"action": "REJECT"})

    response = admin_client.get(f"{PATH}/{question_id}/reviews")

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["action"] == "REJECT"


def test_get_question_reviews_requires_admin(client):
    response = client.get(f"{PATH}/99999/reviews")

    assert response.status_code == 401


def test_get_related_questions(admin_client, client):
    create_response = _post(admin_client, "関連元質問", "関連元回答")
    question_id = create_response.json()[Key.ID]

    response = client.get(f"{PATH}/{question_id}/related")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_update_question_not_found(admin_client):
    response = admin_client.put(
        f"{PATH}/99999",
        json={
            Key.QUESTION: "更新後質問",
            Key.ANSWER: "更新後回答",
        },
    )

    assert response.status_code == 404


def test_delete_question_not_found(admin_client):
    response = admin_client.delete(f"{PATH}/99999")

    assert response.status_code == 404


def test_search_questions(admin_client):
    create_response = _post(admin_client, "検索対象質問", "検索対象回答")

    assert create_response.status_code == 201

    question_id = create_response.json()[Key.ID]

    response = admin_client.post(
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


def test_search_questions_excludes_unreviewed_for_non_admin(admin_client, client):
    import_response = _post_import(
        admin_client,
        [("未承認検索対象質問", "未承認検索対象回答")],
        status="UNREVIEWED",
    )
    question_id = import_response.json()[Key.QUESTIONS][0][Key.ID]

    non_admin_response = client.post(
        SEARCH_PATH,
        json={"query": "未承認検索対象質問に似た質問", "limit": 20},
    )
    admin_response = admin_client.post(
        SEARCH_PATH,
        json={"query": "未承認検索対象質問に似た質問", "limit": 20},
    )

    non_admin_ids = [item[Key.ID] for item in non_admin_response.json()]
    admin_ids = [item[Key.ID] for item in admin_response.json()]

    assert question_id not in non_admin_ids
    assert question_id in admin_ids


def test_create_question_embedding_failure_returns_503(admin_client, monkeypatch):
    def _raise(texts):
        raise EmbeddingGenerationError("boom")

    monkeypatch.setattr(embedding_service, "create_embeddings", _raise)

    response = _post(admin_client, "質問", "回答")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Embedding generation failed. Please try again later."
    }

    list_response = admin_client.get(PATH)

    assert list_response.json()["items"] == []


def test_search_questions_embedding_failure_returns_503(client, monkeypatch):
    def _raise(texts):
        raise EmbeddingGenerationError("boom")

    monkeypatch.setattr(embedding_service, "create_embeddings", _raise)

    response = client.post(SEARCH_PATH, json={"query": "質問"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Embedding generation failed. Please try again later."
    }


def test_update_question_embedding_failure_returns_503(admin_client, monkeypatch):
    create_response = _post(admin_client, "更新前質問", "更新前回答")
    question_id = create_response.json()[Key.ID]

    def _raise(texts):
        raise EmbeddingGenerationError("boom")

    monkeypatch.setattr(embedding_service, "create_embeddings", _raise)

    response = admin_client.put(
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

    get_response = admin_client.get(f"{PATH}/{question_id}")

    assert get_response.json()[Key.QUESTION] == "更新前質問"
    assert get_response.json()[Key.ANSWER] == "更新前回答"


def test_import_questions_embedding_failure_returns_503(admin_client, monkeypatch):
    def _raise(texts):
        raise EmbeddingGenerationError("boom")

    monkeypatch.setattr(embedding_service, "create_embeddings", _raise)

    response = _post_import(admin_client, [("一括質問1", "一括回答1")])

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Embedding generation failed. Please try again later."
    }

    list_response = admin_client.get(PATH)

    assert list_response.json()["items"] == []


def test_delete_question_removes_embeddings(admin_client, db):
    create_response = _post(admin_client, "削除対象質問", "削除対象回答")
    question_id = create_response.json()[Key.ID]

    response = admin_client.delete(f"{PATH}/{question_id}")

    assert response.status_code == 204

    remaining = (
        db.query(QuestionEmbedding)
        .filter(QuestionEmbedding.question_id == question_id)
        .all()
    )

    assert remaining == []


def test_create_question_response_includes_concepts_and_language(admin_client):
    response = _post(admin_client, "概念テスト質問", "概念テスト回答")

    data = response.json()

    assert data["concepts"] == ["概念A", "概念B"]
    assert data["language"] == "ja"


def test_get_questions_response_includes_concepts(admin_client):
    _post(admin_client, "一覧概念質問", "一覧概念回答")

    response = admin_client.get(PATH, params={"keyword": "一覧概念質問"})

    assert response.json()["items"][0]["concepts"] == ["概念A", "概念B"]


BULK_DELETE_PATH = f"{PATH}/bulk-delete"
BULK_REVIEW_PATH = f"{PATH}/bulk-review"
CONCEPTS_EXTRACT_PATH = f"{PATH}/concepts/extract"


def test_bulk_delete_questions(admin_client):
    id1 = _post(admin_client, "一括削除1", "回答1").json()[Key.ID]
    id2 = _post(admin_client, "一括削除2", "回答2").json()[Key.ID]

    response = admin_client.post(
        BULK_DELETE_PATH, json={"question_ids": [id1, id2, 99999]}
    )

    assert response.status_code == 200

    data = response.json()
    assert data["deleted_count"] == 2
    assert data["not_found_ids"] == [99999]


def test_bulk_delete_questions_requires_admin(client):
    response = client.post(BULK_DELETE_PATH, json={"question_ids": [1]})

    assert response.status_code == 401


def test_bulk_delete_questions_forbidden_for_non_admin(user_client):
    response = user_client.post(BULK_DELETE_PATH, json={"question_ids": [1]})

    assert response.status_code == 403


def test_bulk_delete_questions_empty_list_rejected(admin_client):
    response = admin_client.post(BULK_DELETE_PATH, json={"question_ids": []})

    assert response.status_code == 422


def test_bulk_review_questions_approve(admin_client):
    id1 = _post_import(admin_client, [("一括承認1", "回答1")]).json()["questions"][0][
        Key.ID
    ]
    id2 = _post_import(admin_client, [("一括承認2", "回答2")]).json()["questions"][0][
        Key.ID
    ]

    response = admin_client.post(
        BULK_REVIEW_PATH,
        json={"question_ids": [id1, id2, 99999], "action": "APPROVE"},
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data["questions"]) == 2
    assert all(q[Key.STATUS] == "APPROVED" for q in data["questions"])
    assert data["not_found_ids"] == [99999]


def test_bulk_review_questions_reject(admin_client):
    id1 = _post(admin_client, "一括却下1", "回答1").json()[Key.ID]

    response = admin_client.post(
        BULK_REVIEW_PATH, json={"question_ids": [id1], "action": "REJECT"}
    )

    assert response.status_code == 200
    assert response.json()["questions"][0][Key.STATUS] == "REJECTED"


def test_bulk_review_questions_edit_approve_rejected(admin_client):
    id1 = _post(admin_client, "質問", "回答").json()[Key.ID]

    response = admin_client.post(
        BULK_REVIEW_PATH, json={"question_ids": [id1], "action": "EDIT_APPROVE"}
    )

    assert response.status_code == 422


def test_bulk_review_questions_requires_admin(client):
    response = client.post(
        BULK_REVIEW_PATH, json={"question_ids": [1], "action": "APPROVE"}
    )

    assert response.status_code == 401


def test_extract_concepts(admin_client):
    import_response = _post_import(
        admin_client, [("未抽出質問", "回答")], status="UNREVIEWED"
    )
    id1 = import_response.json()["questions"][0][Key.ID]

    response = admin_client.post(
        CONCEPTS_EXTRACT_PATH, json={"question_ids": [id1]}
    )

    assert response.status_code == 200

    data = response.json()["results"]
    assert data[0]["question_id"] == id1
    assert data[0]["success"] is True
    assert data[0]["concepts"] == ["概念A", "概念B"]

    detail_response = admin_client.get(f"{PATH}/{id1}")
    assert detail_response.json()["concepts"] == ["概念A", "概念B"]


def test_extract_concepts_requires_admin(client):
    response = client.post(CONCEPTS_EXTRACT_PATH, json={"question_ids": [1]})

    assert response.status_code == 401


def test_extract_concepts_forbidden_for_non_admin(user_client):
    response = user_client.post(CONCEPTS_EXTRACT_PATH, json={"question_ids": [1]})

    assert response.status_code == 403


def test_extract_concepts_not_found(admin_client):
    response = admin_client.post(
        CONCEPTS_EXTRACT_PATH, json={"question_ids": [99999]}
    )

    assert response.status_code == 200

    data = response.json()["results"][0]
    assert data["success"] is False


def test_create_question_has_empty_retrieved_questions(admin_client):
    response = _post(admin_client, "普通の質問", "普通の回答")

    assert response.json()["retrieved_questions"] == []


def test_get_question_detail_includes_retrieved_questions(admin_client, db):
    referenced = question_repository.create_question(
        db, question="参照質問", answer="参照回答"
    )
    rag_question = question_repository.create_question(
        db,
        question="RAG質問",
        answer="RAG回答",
        status="UNREVIEWED",
        source="RAG_RESULT",
        retrieved_question_ids=[referenced.id],
    )
    db.commit()

    response = admin_client.get(f"{PATH}/{rag_question.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "RAG_RESULT"
    assert body["retrieved_questions"] == [
        {"id": referenced.id, "question": "参照質問"}
    ]


def test_get_questions_list_includes_retrieved_questions(admin_client, db):
    referenced = question_repository.create_question(
        db, question="参照質問2", answer="参照回答2"
    )
    question_repository.create_question(
        db,
        question="RAG質問2",
        answer="RAG回答2",
        status="UNREVIEWED",
        source="RAG_RESULT",
        retrieved_question_ids=[referenced.id],
    )
    db.commit()

    response = admin_client.get(PATH, params={"keyword": "RAG質問2"})

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["retrieved_questions"] == [
        {"id": referenced.id, "question": "参照質問2"}
    ]
