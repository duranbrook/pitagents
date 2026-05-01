import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

SHOP_ID = "00000000-0000-0000-0000-000000000099"


def test_list_columns_returns_existing(client, auth_headers, mock_db):
    col = MagicMock()
    col.id = uuid.uuid4()
    col.shop_id = uuid.UUID(SHOP_ID)
    col.name = "Drop-Off"
    col.position = 0
    col.created_at = datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
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
    col.created_at = datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
    mock_db.execute.return_value.scalar_one_or_none.return_value = col
    resp = client.post(
        "/job-cards/columns",
        json={"name": "Drop-Off", "position": 0},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Drop-Off"


def test_update_column(client, auth_headers, mock_db):
    col = MagicMock()
    col.id = uuid.uuid4()
    col.shop_id = uuid.UUID(SHOP_ID)
    col.name = "In Progress"
    col.position = 1
    col.created_at = None
    mock_db.execute.return_value.scalar_one_or_none.return_value = col
    resp = client.patch(
        f"/job-cards/columns/{col.id}",
        json={"name": "In Progress"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "In Progress"


def test_update_column_not_found(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    resp = client.patch(
        f"/job-cards/columns/{uuid.uuid4()}",
        json={"name": "Ghost"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_delete_column(client, auth_headers, mock_db):
    col = MagicMock()
    col.id = uuid.uuid4()
    col.shop_id = uuid.UUID(SHOP_ID)
    mock_db.execute.return_value.scalar_one_or_none.return_value = col
    resp = client.delete(f"/job-cards/columns/{col.id}", headers=auth_headers)
    assert resp.status_code == 204


def test_delete_column_not_found(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    resp = client.delete(f"/job-cards/columns/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


def test_patch_invalid_uuid_returns_422(client, auth_headers, mock_db):
    resp = client.patch(
        "/job-cards/columns/not-a-uuid",
        json={"name": "x"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_list_job_cards_empty(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    resp = client.get("/job-cards", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

def test_create_job_card(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    from datetime import datetime, timezone
    card = MagicMock()
    card.id = uuid.uuid4()
    card.shop_id = uuid.UUID(SHOP_ID)
    card.number = "JC-0001"
    card.customer_id = None
    card.vehicle_id = None
    card.column_id = None
    card.technician_ids = []
    card.services = []
    card.parts = []
    card.notes = None
    card.status = "active"
    card.created_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    card.updated_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    mock_db.execute.return_value.scalar_one_or_none.return_value = card
    mock_db.execute.return_value.scalar.return_value = 0
    resp = client.post("/job-cards", json={}, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["number"] == "JC-0001"

def test_get_job_card_404(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    resp = client.get(f"/job-cards/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
