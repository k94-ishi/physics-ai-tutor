def test_health_check(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_db_health_check(client):
    response = client.get("/api/v1/db-health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}
