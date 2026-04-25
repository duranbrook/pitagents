import os
import uuid
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
    await engine.dispose()
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def customer_id(client):
    resp = await client.post(
        "/customers",
        json={"name": "Vehicle Owner", "phone": "+15550000001"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 201
    return resp.json()["customer_id"]


@pytest.mark.asyncio
async def test_create_vehicle_returns_201(client, customer_id):
    unique_vin = "1HGBH41J" + uuid.uuid4().hex[:9].upper()
    resp = await client.post(
        f"/customers/{customer_id}/vehicles",
        json={"year": 2021, "make": "Honda", "model": "Civic", "trim": "LX", "vin": unique_vin, "color": "Silver"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["year"] == 2021
    assert data["make"] == "Honda"
    assert data["model"] == "Civic"
    assert data["trim"] == "LX"
    assert data["vin"] == unique_vin
    assert data["customer_id"] == customer_id
    assert "vehicle_id" in data


@pytest.mark.asyncio
async def test_create_vehicle_minimal(client, customer_id):
    resp = await client.post(
        f"/customers/{customer_id}/vehicles",
        json={"year": 2018, "make": "Ford", "model": "F-150"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["trim"] is None
    assert data["vin"] is None


@pytest.mark.asyncio
async def test_list_vehicles(client, customer_id):
    await client.post(
        f"/customers/{customer_id}/vehicles",
        json={"year": 2020, "make": "Toyota", "model": "Camry"},
        headers=_auth_headers(),
    )
    resp = await client.get(f"/customers/{customer_id}/vehicles", headers=_auth_headers())
    assert resp.status_code == 200
    vehicles = resp.json()
    assert isinstance(vehicles, list)
    assert any(v["make"] == "Toyota" for v in vehicles)


@pytest.mark.asyncio
async def test_delete_vehicle_returns_204(client, customer_id):
    create_resp = await client.post(
        f"/customers/{customer_id}/vehicles",
        json={"year": 2015, "make": "Chevy", "model": "Malibu"},
        headers=_auth_headers(),
    )
    vehicle_id = create_resp.json()["vehicle_id"]
    del_resp = await client.delete(f"/vehicles/{vehicle_id}", headers=_auth_headers())
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_nonexistent_vehicle_returns_404(client):
    resp = await client.delete(
        "/vehicles/00000000-0000-0000-0000-000000000000",
        headers=_auth_headers(),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_vehicle_reports_empty(client, customer_id):
    create_resp = await client.post(
        f"/customers/{customer_id}/vehicles",
        json={"year": 2022, "make": "Kia", "model": "Soul"},
        headers=_auth_headers(),
    )
    vehicle_id = create_resp.json()["vehicle_id"]
    resp = await client.get(f"/vehicles/{vehicle_id}/reports", headers=_auth_headers())
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_vehicles_requires_auth(client, customer_id):
    resp = await client.get(f"/customers/{customer_id}/vehicles")
    assert resp.status_code == 401
