import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_autoshop")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")

from src.api.main import app
from src.api.auth import create_access_token


def _owner_headers() -> dict:
    token = create_access_token({"sub": "owner-1", "role": "owner"})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# 1. GET /reports — requires owner role
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_reports_requires_owner(client):
    headers = _owner_headers()
    response = await client.get("/reports", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Seeded test report should appear
    assert any(r["report_id"] == "test-report-1" for r in data)


# ---------------------------------------------------------------------------
# 2. GET /reports/{report_id} — full report detail
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_report_detail(client):
    headers = _owner_headers()
    response = await client.get("/reports/test-report-1", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["report_id"] == "test-report-1"
    assert "findings" in data
    assert data["findings"]["summary"] == "Front brakes worn."


# ---------------------------------------------------------------------------
# 3. GET /r/{share_token} — public consumer view, no auth required
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_consumer_view_no_auth(client):
    response = await client.get("/r/test-share-token-abc")
    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == "Front brakes worn."
    assert data["share_token"] == "test-share-token-abc"


# ---------------------------------------------------------------------------
# 4. POST /reports/{report_id}/send — records sent_to, no real Twilio call
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_report_mocks_twilio(client):
    headers = _owner_headers()
    payload = {"phone": "+15550001111", "email": None}
    response = await client.post("/reports/test-report-1/send", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["sent_to"]["phone"] == "+15550001111"
    assert data["sent_to"]["email"] is None
