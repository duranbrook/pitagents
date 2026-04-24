"""Tests for the quote REST API endpoints."""
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Ensure env vars are set before importing the app
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_autoshop")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")

from src.api.main import app
from src.api.auth import create_access_token
from src.db.base import get_db, Base

TEST_DB = os.environ["DATABASE_URL"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth_headers(role: str = "owner") -> dict:
    user_id = "00000000-0000-0000-0000-000000000001"
    token = create_access_token({"sub": user_id, "role": role, "email": "owner@shop.com"})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client():
    """Provide an AsyncClient with a fresh DB engine for isolation across tests."""
    # Create a fresh engine so each test gets its own connection pool tied to
    # the current event loop (avoids asyncpg "another operation in progress" errors).
    engine = create_async_engine(TEST_DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with maker() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = _override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()


# ---------------------------------------------------------------------------
# POST /quotes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quote_api_create_returns_201(client):
    headers = _auth_headers()
    response = await client.post("/quotes", json={}, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert "quote_id" in data
    assert data["status"] == "draft"


# ---------------------------------------------------------------------------
# GET /quotes/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quote_api_get_returns_quote(client):
    headers = _auth_headers()

    # Create a quote
    create_resp = await client.post("/quotes", json={}, headers=headers)
    assert create_resp.status_code == 201
    quote_id = create_resp.json()["quote_id"]

    # Retrieve it
    get_resp = await client.get(f"/quotes/{quote_id}", headers=headers)
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["quote_id"] == quote_id
    assert data["status"] == "draft"


# ---------------------------------------------------------------------------
# GET /quotes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quote_api_list_returns_quotes(client):
    headers = _auth_headers()

    # Create a quote
    create_resp = await client.post("/quotes", json={}, headers=headers)
    assert create_resp.status_code == 201
    quote_id = create_resp.json()["quote_id"]

    # List all quotes
    list_resp = await client.get("/quotes", headers=headers)
    assert list_resp.status_code == 200
    quotes = list_resp.json()
    assert isinstance(quotes, list)
    ids = [q["quote_id"] for q in quotes]
    assert quote_id in ids


# ---------------------------------------------------------------------------
# PUT /quotes/{id}/finalize
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quote_api_finalize_returns_200(client):
    headers = _auth_headers()

    # Create a quote
    create_resp = await client.post("/quotes", json={}, headers=headers)
    assert create_resp.status_code == 201
    quote_id = create_resp.json()["quote_id"]

    # Verify it's a draft first
    get_resp = await client.get(f"/quotes/{quote_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "draft"

    # Finalize it
    finalize_resp = await client.put(f"/quotes/{quote_id}/finalize", headers=headers)
    assert finalize_resp.status_code == 200
    data = finalize_resp.json()
    assert data["status"] == "final"
    assert data["quote_id"] == quote_id


# ---------------------------------------------------------------------------
# Auth required
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quote_api_requires_auth(client):
    response = await client.post("/quotes", json={})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# 404 cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quote_api_get_not_found(client):
    headers = _auth_headers()
    nonexistent = "00000000-0000-0000-0000-000000000099"
    response = await client.get(f"/quotes/{nonexistent}", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_quote_api_session_quote_not_found(client):
    headers = _auth_headers()
    nonexistent = "00000000-0000-0000-0000-000000000099"
    response = await client.get(f"/sessions/{nonexistent}/quote", headers=headers)
    assert response.status_code == 404
