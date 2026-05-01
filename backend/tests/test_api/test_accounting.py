import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock

SHOP_ID = "00000000-0000-0000-0000-000000000099"


def _make_expense(**kwargs) -> MagicMock:
    exp = MagicMock()
    exp.id = kwargs.get("id", uuid.uuid4())
    exp.shop_id = uuid.UUID(SHOP_ID)
    exp.description = kwargs.get("description", "Oil and filter")
    exp.amount = kwargs.get("amount", Decimal("45.00"))
    exp.category = kwargs.get("category", "Parts")
    exp.vendor = kwargs.get("vendor", None)
    exp.expense_date = kwargs.get("expense_date", date(2026, 5, 1))
    exp.qb_synced = kwargs.get("qb_synced", False)
    exp.created_at = kwargs.get("created_at", datetime(2026, 5, 1, 9, 0, 0, tzinfo=timezone.utc))
    return exp


def test_list_expenses_empty(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    resp = client.get("/accounting/expenses", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_expense(client, auth_headers, mock_db):
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    resp = client.post(
        "/accounting/expenses",
        json={
            "description": "Brake pads",
            "amount": 120.50,
            "category": "Parts",
            "vendor": "NAPA Auto Parts",
            "expense_date": "2026-05-01",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert "shop_id" in data
    assert data["description"] == "Brake pads"
    assert data["category"] == "Parts"
    assert data["vendor"] == "NAPA Auto Parts"
    assert data["qb_synced"] is False


def test_create_expense_invalid_category(client, auth_headers, mock_db):
    resp = client.post(
        "/accounting/expenses",
        json={
            "description": "Something",
            "amount": 10.00,
            "category": "InvalidCat",
            "expense_date": "2026-05-01",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_pl_summary_returns_structure(client, auth_headers, mock_db):
    # Each aggregate query calls scalar() — configure the mock to return 0
    mock_db.execute.return_value.scalar.return_value = 0

    resp = client.get("/accounting/pl?period=mtd", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "revenue" in data
    assert "expenses" in data
    assert "net_profit" in data
    assert "outstanding_ar" in data
    assert data["period"] == "mtd"


def test_pl_summary_unknown_period(client, auth_headers, mock_db):
    resp = client.get("/accounting/pl?period=badperiod", headers=auth_headers)
    assert resp.status_code == 400
