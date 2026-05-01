import uuid
from unittest.mock import MagicMock, AsyncMock

SHOP_ID = "00000000-0000-0000-0000-000000000099"


def test_list_columns_returns_existing(client, auth_headers, mock_db):
    col = MagicMock()
    col.id = uuid.uuid4()
    col.shop_id = uuid.UUID(SHOP_ID)
    col.name = "Drop-Off"
    col.position = 0
    col.created_at = "2026-05-01T00:00:00+00:00"
    mock_db.execute.return_value.scalars.return_value.all.return_value = [col]
    resp = client.get("/job-cards/columns", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "Drop-Off"


def test_list_columns_seeds_defaults_when_empty(client, auth_headers, mock_db):
    # First call returns empty (triggers seeding), subsequent refreshes use mocks
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.refresh = AsyncMock()
    resp = client.get("/job-cards/columns", headers=auth_headers)
    assert resp.status_code == 200
    # Should have seeded 4 default columns
    assert len(resp.json()) == 4
    names = [c["name"] for c in resp.json()]
    assert "Drop-Off" in names
    assert "Ready for Pickup" in names


def test_create_column(client, auth_headers, mock_db):
    col = MagicMock()
    col.id = uuid.uuid4()
    col.shop_id = uuid.UUID(SHOP_ID)
    col.name = "Drop-Off"
    col.position = 0
    col.created_at = "2026-05-01T00:00:00+00:00"
    mock_db.execute.return_value.scalar_one_or_none.return_value = col
    resp = client.post(
        "/job-cards/columns",
        json={"name": "Drop-Off", "position": 0},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Drop-Off"
