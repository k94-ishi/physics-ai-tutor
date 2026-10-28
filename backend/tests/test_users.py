from datetime import datetime

from fastapi.testclient import TestClient

from physics_ai_tutor.main import app

ME_PATH = "/api/v1/users/me"
PASSWORD_PATH = "/api/v1/users/me/password"
USERS_PATH = "/api/v1/users"

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "adminpass123"
USER_EMAIL = "user@example.com"
USER_PASSWORD = "userpass123"


def test_get_me_returns_current_user(user_client):
    response = user_client.get(ME_PATH)

    assert response.status_code == 200

    data = response.json()

    assert data["role"] == "user"


def test_get_me_requires_authentication(client):
    response = client.get(ME_PATH)

    assert response.status_code == 401


def test_list_users_admin_only(admin_client):
    response = admin_client.get(USERS_PATH)

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_users_forbidden_for_non_admin(user_client):
    response = user_client.get(USERS_PATH)

    assert response.status_code == 403


def test_create_user_admin_only(admin_client):
    response = admin_client.post(
        USERS_PATH,
        json={"email": "new-user@example.com", "password": "newuserpass123"},
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "new-user@example.com"
    assert data["role"] == "user"


def test_create_user_with_admin_role(admin_client):
    response = admin_client.post(
        USERS_PATH,
        json={
            "email": "new-admin@example.com",
            "password": "newadminpass123",
            "role": "admin",
        },
    )

    assert response.status_code == 201
    assert response.json()["role"] == "admin"


def test_create_user_response_includes_created_at(admin_client):
    response = admin_client.post(
        USERS_PATH,
        json={"email": "created-at-check@example.com", "password": "somepassword123"},
    )

    assert response.status_code == 201

    data = response.json()

    assert "created_at" in data
    # Must be a parseable ISO 8601 timestamp, not just any truthy value.
    datetime.fromisoformat(data["created_at"])


def test_create_user_duplicate_email_rejected(admin_client):
    admin_client.post(
        USERS_PATH,
        json={"email": "dup@example.com", "password": "somepassword123"},
    )

    response = admin_client.post(
        USERS_PATH,
        json={"email": "dup@example.com", "password": "somepassword123"},
    )

    assert response.status_code == 409


def test_create_user_forbidden_for_non_admin(user_client):
    response = user_client.post(
        USERS_PATH,
        json={"email": "blocked@example.com", "password": "somepassword123"},
    )

    assert response.status_code == 403


def test_create_user_requires_authentication(client):
    response = client.post(
        USERS_PATH,
        json={"email": "blocked@example.com", "password": "somepassword123"},
    )

    assert response.status_code == 401


def test_create_user_invalid_password_rejected(admin_client):
    response = admin_client.post(
        USERS_PATH,
        json={"email": "short-pw@example.com", "password": "short"},
    )

    assert response.status_code == 422


def test_get_user_by_id_admin_only(admin_client, user_client):
    me_response = user_client.get(ME_PATH)
    user_id = me_response.json()["id"]

    response = admin_client.get(f"{USERS_PATH}/{user_id}")

    assert response.status_code == 200
    assert response.json()["email"] == USER_EMAIL


def test_get_user_by_id_not_found(admin_client):
    response = admin_client.get(f"{USERS_PATH}/99999")

    assert response.status_code == 404


def test_get_user_by_id_forbidden_for_non_admin(user_client):
    response = user_client.get(f"{USERS_PATH}/1")

    assert response.status_code == 403


def test_delete_user_admin_only(admin_client, user_client):
    me_response = user_client.get(ME_PATH)
    user_id = me_response.json()["id"]

    response = admin_client.delete(f"{USERS_PATH}/{user_id}")

    assert response.status_code == 204
    assert admin_client.get(f"{USERS_PATH}/{user_id}").status_code == 404


def test_delete_user_keeps_review_history(admin_client, db):
    # Create a second admin, let them review a question, then delete them.
    created = admin_client.post(
        USERS_PATH,
        json={
            "email": "reviewer@example.com",
            "password": "reviewerpass1",
            "role": "admin",
        },
    )
    reviewer_id = created.json()["id"]

    reviewer = TestClient(app)
    login = reviewer.post(
        "/api/v1/auth/login",
        json={"email": "reviewer@example.com", "password": "reviewerpass1"},
    )
    assert login.status_code == 200

    question_id = reviewer.post(
        "/api/v1/questions",
        json={"question": "削除される査読者の質問", "answer": "回答"},
    ).json()["id"]
    assert (
        reviewer.post(
            f"/api/v1/questions/{question_id}/review", json={"action": "REJECT"}
        ).status_code
        == 200
    )

    response = admin_client.delete(f"{USERS_PATH}/{reviewer_id}")

    assert response.status_code == 204

    reviews = admin_client.get(f"/api/v1/questions/{question_id}/reviews").json()
    assert len(reviews) == 1
    assert reviews[0]["action"] == "REJECT"
    assert reviews[0]["reviewer_id"] is None


def test_delete_user_not_found(admin_client):
    response = admin_client.delete(f"{USERS_PATH}/99999")

    assert response.status_code == 404


def test_delete_user_self_blocked(admin_client):
    me_response = admin_client.get(ME_PATH)
    admin_id = me_response.json()["id"]

    response = admin_client.delete(f"{USERS_PATH}/{admin_id}")

    assert response.status_code == 400


def test_delete_user_forbidden_for_non_admin(user_client):
    response = user_client.delete(f"{USERS_PATH}/1")

    assert response.status_code == 403


def test_change_password_success(user_client):
    response = user_client.put(
        PASSWORD_PATH,
        json={"current_password": USER_PASSWORD, "new_password": "newpassword456"},
    )

    assert response.status_code == 204

    login_response = user_client.post(
        "/api/v1/auth/login",
        json={"email": USER_EMAIL, "password": "newpassword456"},
    )
    assert login_response.status_code == 200


def test_change_password_wrong_current_password_rejected(user_client):
    response = user_client.put(
        PASSWORD_PATH,
        json={"current_password": "wrongpassword", "new_password": "newpassword456"},
    )

    assert response.status_code == 400


def test_change_password_too_short_rejected(user_client):
    response = user_client.put(
        PASSWORD_PATH,
        json={"current_password": USER_PASSWORD, "new_password": "short"},
    )

    assert response.status_code == 422


def test_change_password_requires_authentication(client):
    response = client.put(
        PASSWORD_PATH,
        json={"current_password": "x", "new_password": "newpassword456"},
    )

    assert response.status_code == 401


def test_get_my_profile_returns_account_details(user_client):
    response = user_client.get("/api/v1/users/me/profile")

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "user@example.com"
    assert body["role"] == "user"
    assert body["auth_provider"] == "password"


def test_get_my_profile_requires_authentication(client):
    assert client.get("/api/v1/users/me/profile").status_code == 401


def test_delete_my_account_removes_user_and_clears_cookie(user_client, db):
    from physics_ai_tutor.models import User

    response = user_client.delete("/api/v1/users/me")

    assert response.status_code == 204
    assert "max-age=0" in response.headers.get("set-cookie", "").lower()
    assert db.query(User).filter_by(email="user@example.com").first() is None

    # The session is gone: the cleared cookie no longer authenticates.
    assert user_client.get("/api/v1/users/me").status_code == 401


def test_delete_my_account_refused_for_admin(admin_client, db):
    from physics_ai_tutor.models import User

    response = admin_client.delete("/api/v1/users/me")

    assert response.status_code == 400
    assert db.query(User).filter_by(email="admin@example.com").first() is not None


def test_delete_my_account_requires_authentication(client):
    assert client.delete("/api/v1/users/me").status_code == 401


def test_delete_my_account_keeps_review_history(user_client, admin_client, db):
    from physics_ai_tutor.models import QuestionReview, User

    created = admin_client.post(
        "/api/v1/questions",
        json={"question": "履歴テスト質問", "answer": "回答"},
    )
    assert created.status_code == 201
    question_id = created.json()["id"]

    # A review written by the soon-to-be-deleted user (role has no bearing
    # on the FK behaviour; write the row directly).
    user = db.query(User).filter_by(email="user@example.com").one()
    db.add(
        QuestionReview(
            question_id=question_id,
            action="APPROVE",
            reviewer_id=user.id,
            language="ja",
        )
    )
    db.commit()

    assert user_client.delete("/api/v1/users/me").status_code == 204

    review = db.query(QuestionReview).filter_by(question_id=question_id).one()
    db.refresh(review)
    assert review.reviewer_id is None
