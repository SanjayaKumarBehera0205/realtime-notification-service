def test_notification_lifecycle(client, user):
    created = client.post(
        "/api/v1/notifications",
        headers=user["headers"],
        json={
            "recipient_id": user["id"],
            "title": "Welcome",
            "message": "Your account is ready.",
            "type": "success",
            "data": {"screen": "dashboard"},
        },
    )
    assert created.status_code == 201
    notification_id = created.json()["id"]

    listed = client.get("/api/v1/notifications?unread_only=true", headers=user["headers"])
    assert listed.status_code == 200
    assert listed.json()["unread"] == 1
    assert listed.json()["items"][0]["type"] == "success"

    marked = client.patch(
        f"/api/v1/notifications/{notification_id}/read", headers=user["headers"]
    )
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True

    deleted = client.delete(
        f"/api/v1/notifications/{notification_id}", headers=user["headers"]
    )
    assert deleted.status_code == 204


def test_notification_requires_authentication(client):
    assert client.get("/api/v1/notifications").status_code == 401


def test_mark_all_notifications_as_read(client, user):
    for number in range(2):
        response = client.post(
            "/api/v1/notifications",
            headers=user["headers"],
            json={
                "recipient_id": user["id"],
                "title": f"Notification {number}",
                "message": "Unread message",
            },
        )
        assert response.status_code == 201

    result = client.patch("/api/v1/notifications/read-all", headers=user["headers"])
    assert result.status_code == 200
    assert result.json()["updated"] == 2
    assert client.get("/api/v1/notifications", headers=user["headers"]).json()["unread"] == 0


def test_websocket_connects_and_answers_ping(client, user):
    with client.websocket_connect(f"/ws/notifications?token={user['token']}") as websocket:
        assert websocket.receive_json()["event"] == "connected"
        websocket.send_text("ping")
        assert websocket.receive_json() == {"event": "pong"}
