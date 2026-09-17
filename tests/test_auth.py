def test_register_login_and_profile(client):
    registered = client.post(
        "/api/v1/auth/register",
        json={"name": "Sanjaya", "email": "sanjaya@example.com", "password": "strongpass123"},
    )
    assert registered.status_code == 201
    assert "password" not in registered.json()

    login = client.post(
        "/api/v1/auth/login",
        data={"username": "sanjaya@example.com", "password": "strongpass123"},
    )
    assert login.status_code == 200
    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert profile.status_code == 200
    assert profile.json()["email"] == "sanjaya@example.com"


def test_duplicate_email_is_rejected(client):
    payload = {"name": "User", "email": "same@example.com", "password": "password123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409
