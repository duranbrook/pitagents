import io
import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

# Ensure env vars are set before importing the app
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_autoshop")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")

from src.api.main import app
from src.api.auth import create_access_token


def _auth_headers(role: str = "owner") -> dict:
    user_id = "owner-1" if role == "owner" else "tech-1"
    token = create_access_token({"sub": user_id, "role": role})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# 1. POST /sessions — create session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_session(client):
    headers = _auth_headers("owner")
    payload = {"shop_id": "shop-abc", "labor_rate": 120.0, "pricing_flag": "shop"}
    response = await client.post("/sessions", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "recording"


# ---------------------------------------------------------------------------
# 2. POST /sessions/{id}/media — upload media
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upload_media(client):
    # First create a session
    headers = _auth_headers("owner")
    session_resp = await client.post(
        "/sessions",
        json={"shop_id": "shop-abc", "labor_rate": 120.0, "pricing_flag": "shop"},
        headers=headers,
    )
    assert session_resp.status_code == 200
    session_id = session_resp.json()["session_id"]

    # Upload a file with mocked S3
    with patch("src.api.sessions.StorageService") as MockStorage:
        MockStorage.return_value.upload = AsyncMock(
            return_value="test-bucket/session-1/audio.mp3"
        )
        file_content = b"fake audio bytes"
        response = await client.post(
            f"/sessions/{session_id}/media",
            headers=headers,
            files={"file": ("audio.mp3", io.BytesIO(file_content), "audio/mpeg")},
            data={"media_type": "audio", "tag": "general"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "media_id" in data
    assert "s3_url" in data


# ---------------------------------------------------------------------------
# 3. GET /sessions/{id} — get session data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_session(client):
    headers = _auth_headers("owner")

    # Create a session first
    session_resp = await client.post(
        "/sessions",
        json={"shop_id": "shop-get", "labor_rate": 110.0, "pricing_flag": "shop"},
        headers=headers,
    )
    assert session_resp.status_code == 200
    session_id = session_resp.json()["session_id"]

    # Retrieve it
    response = await client.get(f"/sessions/{session_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert "status" in data
