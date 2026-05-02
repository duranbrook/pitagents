import os
import uuid
import pytest
from unittest.mock import MagicMock
from passlib.context import CryptContext

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_autoshop")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _make_user(email="owner@shop.com", password="testpass", role="owner", name="Test Owner"):
    u = MagicMock()
    u.id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    u.shop_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
    u.email = email
    u.role = role
    u.name = name
    u.hashed_password = pwd_ctx.hash(password)
    return u


def test_login_returns_token(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = _make_user()
    resp = client.post("/auth/login", json={"email": "owner@shop.com", "password": "testpass"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password_returns_401(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = _make_user()
    resp = client.post("/auth/login", json={"email": "owner@shop.com", "password": "wrongpassword"})
    assert resp.status_code == 401


def test_login_unknown_email_returns_401(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    resp = client.post("/auth/login", json={"email": "nobody@shop.com", "password": "testpass"})
    assert resp.status_code == 401


def test_login_token_contains_shop_id(client, mock_db):
    import jwt as pyjwt
    from src.config import settings
    mock_db.execute.return_value.scalar_one_or_none.return_value = _make_user()
    resp = client.post("/auth/login", json={"email": "owner@shop.com", "password": "testpass"})
    assert resp.status_code == 200
    payload = pyjwt.decode(
        resp.json()["access_token"],
        settings.JWT_SECRET.get_secret_value(),
        algorithms=[settings.JWT_ALGORITHM],
    )
    assert payload.get("shop_id") == "00000000-0000-0000-0000-000000000099"


def test_get_me(client, mock_db, auth_headers):
    mock_db.execute.return_value.scalar_one_or_none.return_value = _make_user()
    resp = client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "owner@shop.com"
    assert data["name"] == "Test Owner"
    assert data["role"] == "owner"


def test_update_profile(client, mock_db, auth_headers):
    mock_db.execute.return_value.scalar_one_or_none.return_value = _make_user()
    resp = client.patch("/auth/profile", json={"name": "New Name"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "owner@shop.com"


def test_change_password_success(client, mock_db, auth_headers):
    mock_db.execute.return_value.scalar_one_or_none.return_value = _make_user()
    resp = client.patch(
        "/auth/password",
        json={"current_password": "testpass", "new_password": "newpass123"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_change_password_wrong_current_returns_400(client, mock_db, auth_headers):
    mock_db.execute.return_value.scalar_one_or_none.return_value = _make_user()
    resp = client.patch(
        "/auth/password",
        json={"current_password": "wrongpass", "new_password": "newpass123"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "incorrect" in resp.json()["detail"].lower()


def test_technician_cannot_access_owner_route(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = _make_user(role="technician")
    login_resp = client.post("/auth/login", json={"email": "tech@shop.com", "password": "testpass"})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    resp = client.get("/reports", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
