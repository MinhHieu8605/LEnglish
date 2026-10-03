from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import Request
from fastapi.testclient import TestClient
import pytest

from app.database.async_db import get_session
from app.features.user.schemas import UserResponse
from app.main import app
from app.middleware.auth import get_current_user
from app.utils.constants import Role


@pytest.fixture
def client():
    async def session_override():
        yield object()

    async def user_override(request: Request):
        request.state.user_id = 7
        request.state.email = "user@example.com"
        request.state.role = "user"

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_current_user] = user_override
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize("user", [None, SimpleNamespace(check_password=lambda _: False)])
def test_invalid_credentials_preserve_client_error(client, monkeypatch, user):
    monkeypatch.setattr(
        "app.features.user.service.async_get_one_record_by", AsyncMock(return_value=user)
    )

    response = client.post(
        "/api/v1/users/login",
        json={"email": "user@example.com", "password": "incorrect"},
    )

    assert response.status_code == 400


def test_google_login_accepts_header_without_body(client, monkeypatch):
    google_login = AsyncMock(return_value=object())
    payload = {"id": 7, "email": "user@example.com", "access_token": "access", "refresh_token": "refresh", "role": "user"}
    monkeypatch.setattr("app.features.user.service.UserService._handle_google_login", google_login)
    monkeypatch.setattr("app.features.user.service.UserService._prepare_login_response", AsyncMock(return_value=payload))
    monkeypatch.setattr("app.features.user.service.UserService.request_event", AsyncMock())

    response = client.post("/api/v1/users/login", headers={"token-google": "google-token"})

    assert response.status_code == 200
    assert response.json() == payload
    assert google_login.await_args.args[0] == "google-token"


def test_login_without_credentials_returns_client_error(client):
    response = client.post("/api/v1/users/login")

    assert response.status_code == 400


def test_duplicate_registration_preserves_client_error(client, monkeypatch):
    monkeypatch.setattr(
        "app.features.user.service.async_get_one_record_by", AsyncMock(return_value=object())
    )

    response = client.post(
        "/api/v1/users/register",
        json={"email": "user@example.com", "full_name": "User", "password": "password123"},
    )

    assert response.status_code == 400


@pytest.mark.parametrize(
    ("email", "password", "invalid_field"),
    [("invalid-email", "password123", "email"), ("user@example.com", "short", "password")],
)
def test_registration_rejects_invalid_input_before_service(client, monkeypatch, email, password, invalid_field):
    register = AsyncMock()
    monkeypatch.setattr("app.features.user.service.UserService.register", register)

    response = client.post(
        "/api/v1/users/register",
        json={"email": email, "full_name": "User", "password": password},
    )

    assert response.status_code == 422
    assert ["body", invalid_field] in [error["loc"] for error in response.json()["detail"]]
    register.assert_not_awaited()


def test_update_profile_accepts_name_without_deleted(client, monkeypatch):
    profile = UserResponse(
        id=7, email="user@example.com", full_name="New name", avatar_url=None,
        role=Role.USER, deleted=False, created_time=None, updated_time=None,
    )
    update = AsyncMock(return_value=profile)
    monkeypatch.setattr("app.features.user.service.UserService.update_user", update)

    response = client.put("/api/v1/users/7", json={"full_name": "New name"})

    assert response.status_code == 200
    assert response.json()["full_name"] == "New name"
    assert update.await_args.args[1].model_dump(exclude_unset=True) == {"full_name": "New name"}
