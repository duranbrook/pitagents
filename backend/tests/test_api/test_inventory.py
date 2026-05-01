import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock

SHOP_ID = "00000000-0000-0000-0000-000000000099"


def _make_item(**kwargs) -> MagicMock:
    item = MagicMock()
    item.id = kwargs.get("id", uuid.uuid4())
    item.shop_id = uuid.UUID(SHOP_ID)
    item.name = kwargs.get("name", "Oil Filter")
    item.sku = kwargs.get("sku", "OF-1234")
    item.category = kwargs.get("category", "Filters")
    item.quantity = kwargs.get("quantity", 10)
    item.reorder_at = kwargs.get("reorder_at", 3)
    item.cost_price = kwargs.get("cost_price", Decimal("8.50"))
    item.sell_price = kwargs.get("sell_price", Decimal("15.00"))
    item.vendor_id = kwargs.get("vendor_id", None)
    item.notes = kwargs.get("notes", None)
    item.created_at = kwargs.get("created_at", datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc))
    item.updated_at = kwargs.get("updated_at", datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc))
    return item


def test_list_inventory_empty(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    resp = client.get("/inventory", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_inventory_item(client, auth_headers, mock_db):
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.refresh = AsyncMock()
    resp = client.post(
        "/inventory",
        json={
            "name": "Brake Pad Set",
            "sku": "BP-999",
            "category": "Brakes",
            "quantity": 5,
            "reorder_at": 2,
            "cost_price": "20.00",
            "sell_price": "45.00",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert "shop_id" in data
    assert data["name"] == "Brake Pad Set"


def test_adjust_stock(client, auth_headers, mock_db):
    item_id = uuid.uuid4()
    item = _make_item(id=item_id, quantity=10)

    mock_db.execute.return_value.scalar_one_or_none.return_value = item
    mock_db.commit = AsyncMock()

    resp = client.post(
        f"/inventory/{item_id}/adjust",
        json={"delta": -3, "reason": "used in repair"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["quantity"] == 7
