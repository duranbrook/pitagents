import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Ensure env vars are set before importing the app
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_autoshop")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")

from src.api.main import app


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_login_returns_token(client):
    response = await client.post("/auth/login", json={"email": "owner@shop.com", "password": "testpass"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client):
    response = await client.post("/auth/login", json={"email": "owner@shop.com", "password": "wrongpassword"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_technician_cannot_access_owner_route(client):
    # Login as technician
    login_response = await client.post("/auth/login", json={"email": "tech@shop.com", "password": "testpass"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Attempt to access owner-only route
    response = await client.get("/reports", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
