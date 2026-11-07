def test_missing_key_is_rejected(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_invalid_key_is_rejected(client):
    response = client.get("/api/v1/auth/me", headers={"X-API-Key": "wrong"})
    assert response.status_code == 401


def test_valid_key_returns_actor(client, readonly_headers):
    response = client.get("/api/v1/auth/me", headers=readonly_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "read_only"
    assert body["role"] == "read_only"


def test_role_enforcement(client, readonly_headers, admin_headers):
    denied = client.get("/api/v1/audit", headers=readonly_headers)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "forbidden"

    allowed = client.get("/api/v1/audit", headers=admin_headers)
    assert allowed.status_code == 200
