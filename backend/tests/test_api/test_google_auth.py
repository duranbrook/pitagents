import uuid
from unittest.mock import MagicMock, patch
from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _make_user(email="owner@shop.com", password="testpass", role="owner", name="Test Owner"):
    u = MagicMock()
    u.id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    u.shop_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
    u.email = email
    u.role = role
    u.name = name
    u.hashed_password = pwd_ctx.hash(password)
    u.google_id = None
    return u


def test_google_login_existing_user_returns_token(client, mock_db):
    user = _make_user()
    # First call (by google_id) returns None, second call (by email) returns user
    mock_db.execute.return_value.scalar_one_or_none.side_effect = [None, user]

    with patch("src.api.auth.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.return_value = {
            "sub": "google-sub-12345",
            "email": "owner@shop.com",
        }
        resp = client.post("/auth/google", json={"id_token": "fake-google-id-token"})

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_google_login_unknown_email_returns_401(client, mock_db):
    # Both lookups (by google_id and by email) return None
    mock_db.execute.return_value.scalar_one_or_none.side_effect = [None, None]

    with patch("src.api.auth.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.return_value = {
            "sub": "google-sub-unknown",
            "email": "nobody@example.com",
        }
        resp = client.post("/auth/google", json={"id_token": "fake-google-id-token"})

    assert resp.status_code == 401


def test_google_login_invalid_token_returns_401(client, mock_db):
    with patch("src.api.auth.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.side_effect = ValueError("bad token")
        resp = client.post("/auth/google", json={"id_token": "invalid-token"})

    assert resp.status_code == 401
