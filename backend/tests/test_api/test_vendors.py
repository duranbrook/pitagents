import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock

SHOP_ID = "00000000-0000-0000-0000-000000000099"


def _make_vendor(**kwargs) -> MagicMock:
    vendor = MagicMock()
    vendor.id = kwargs.get("id", uuid.uuid4())
    vendor.shop_id = uuid.UUID(SHOP_ID)
    vendor.name = kwargs.get("name", "AutoZone")
    vendor.category = kwargs.get("category", "Parts")
    vendor.phone = kwargs.get("phone", None)
    vendor.email = kwargs.get("email", None)
    vendor.website = kwargs.get("website", None)
    vendor.address = kwargs.get("address", None)
    vendor.rep_name = kwargs.get("rep_name", None)
    vendor.rep_phone = kwargs.get("rep_phone", None)
    vendor.account_number = kwargs.get("account_number", None)
    vendor.notes = kwargs.get("notes", None)
    vendor.source = kwargs.get("source", "manual")
    vendor.ytd_spend = kwargs.get("ytd_spend", Decimal("0.00"))
    vendor.order_count = kwargs.get("order_count", 0)
    vendor.last_order_at = kwargs.get("last_order_at", None)
    vendor.created_at = kwargs.get("created_at", datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc))
    return vendor


def test_list_vendors_empty(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    resp = client.get("/vendors", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_vendor(client, auth_headers, mock_db):
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.refresh = AsyncMock()
    resp = client.post(
        "/vendors",
        json={
            "name": "O'Reilly Auto Parts",
            "category": "Parts",
            "phone": "555-1234",
            "email": "orders@oreilly.com",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert "shop_id" in data
    assert data["name"] == "O'Reilly Auto Parts"


def test_get_vendor_404(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    random_id = str(uuid.uuid4())
    resp = client.get(f"/vendors/{random_id}", headers=auth_headers)
    assert resp.status_code == 404
