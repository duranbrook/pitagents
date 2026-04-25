import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_autoshop")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")

from src.api.main import app
from src.api.auth import create_access_token
from src.db.base import engine

SHOP_ID = "00000000-0000-0000-0000-000000000099"


def _auth_headers() -> dict:
    token = create_access_token({
        "sub": "00000000-0000-0000-0000-000000000001",
        "shop_id": SHOP_ID,
        "role": "owner",
    })
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(autouse=True)
async def reset_engine():
    """Dispose connection pool before each test to avoid cross-loop contamination."""
    await engine.dispose()
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_create_customer_returns_201(client):
    resp = await client.post(
        "/customers",
        json={"name": "Mike Rodriguez", "email": "mike@example.com", "phone": "+15551234567"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Mike Rodriguez"
    assert data["email"] == "mike@example.com"
    assert data["shop_id"] == SHOP_ID
    assert "customer_id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_customer_name_only(client):
    resp = await client.post("/customers", json={"name": "Name Only"}, headers=_auth_headers())
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Name Only"
    assert data["email"] is None
    assert data["phone"] is None


@pytest.mark.asyncio
async def test_list_customers_returns_own_shop(client):
    # Create a customer first
    await client.post("/customers", json={"name": "List Test"}, headers=_auth_headers())
    resp = await client.get("/customers", headers=_auth_headers())
    assert resp.status_code == 200
    customers = resp.json()
    assert isinstance(customers, list)
    # Every returned customer belongs to our shop
    for c in customers:
        assert c["shop_id"] == SHOP_ID


@pytest.mark.asyncio
async def test_delete_customer_returns_204(client):
    create_resp = await client.post("/customers", json={"name": "To Delete"}, headers=_auth_headers())
    customer_id = create_resp.json()["customer_id"]
    del_resp = await client.delete(f"/customers/{customer_id}", headers=_auth_headers())
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_nonexistent_customer_returns_404(client):
    resp = await client.delete(
        "/customers/00000000-0000-0000-0000-000000000000",
        headers=_auth_headers(),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_customer_requires_auth(client):
    resp = await client.post("/customers", json={"name": "No Auth"})
    assert resp.status_code == 401
