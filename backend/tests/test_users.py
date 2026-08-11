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

    assert data["email"] == USER_EMAIL
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
