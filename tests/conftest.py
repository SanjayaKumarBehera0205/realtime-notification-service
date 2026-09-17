import os

os.environ["DATABASE_URL"] = "sqlite:///./test_notifications.db"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["REDIS_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import engine
from app.main import app


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def create_user(client: TestClient, email: str = "user@example.com") -> tuple[int, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Test User", "email": email, "password": "password123"},
    )
    user_id = response.json()["id"]
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "password123"},
    )
    return user_id, login.json()["access_token"]


@pytest.fixture
def user(client: TestClient):
    user_id, token = create_user(client)
    return {"id": user_id, "token": token, "headers": {"Authorization": f"Bearer {token}"}}
