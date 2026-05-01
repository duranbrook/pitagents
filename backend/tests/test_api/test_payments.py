import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock

SHOP_ID = "00000000-0000-0000-0000-000000000099"
INVOICE_ID = "00000000-0000-0000-0000-000000000010"


def _make_invoice(**kwargs) -> MagicMock:
    inv = MagicMock()
    inv.id = kwargs.get("id", uuid.UUID(INVOICE_ID))
    inv.shop_id = uuid.UUID(SHOP_ID)
    inv.number = kwargs.get("number", "INV-0001")
    inv.status = kwargs.get("status", "pending")
    inv.total = kwargs.get("total", Decimal("200.00"))
    inv.amount_paid = kwargs.get("amount_paid", Decimal("0.00"))
    inv.stripe_payment_link = kwargs.get("stripe_payment_link", None)
    return inv


def _make_payment_event(**kwargs) -> MagicMock:
    evt = MagicMock()
    evt.id = kwargs.get("id", uuid.uuid4())
    evt.invoice_id = kwargs.get("invoice_id", uuid.UUID(INVOICE_ID))
    evt.amount = kwargs.get("amount", Decimal("50.00"))
    evt.method = kwargs.get("method", "cash")
    evt.recorded_at = kwargs.get(
        "recorded_at", datetime(2026, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
    )
    evt.notes = kwargs.get("notes", None)
    return evt


def test_payments_summary(client, auth_headers, mock_db):
    # All four aggregate queries call .scalar() — return 0 for each
    mock_db.execute.return_value.scalar.return_value = 0

    resp = client.get("/payments/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "outstanding" in data
    assert "overdue" in data
    assert "collected_this_month" in data
    assert "total_invoices" in data
    assert data["outstanding"] == 0.0
    assert data["overdue"] == 0.0
    assert data["collected_this_month"] == 0.0
    assert data["total_invoices"] == 0


def test_list_payment_history(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []

    resp = client.get("/payments/history", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_payment_history_with_events(client, auth_headers, mock_db):
    evt = _make_payment_event()
    mock_db.execute.return_value.scalars.return_value.all.return_value = [evt]

    resp = client.get("/payments/history", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["method"] == "cash"
    assert data[0]["amount"] == 50.0
    assert "invoice_id" in data[0]
    assert "recorded_at" in data[0]


def test_chase_invoice_not_found(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    resp = client.post(f"/payments/chase/{INVOICE_ID}", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Invoice not found"


def test_chase_invoice_already_paid(client, auth_headers, mock_db):
    inv = _make_invoice(status="paid")
    mock_db.execute.return_value.scalar_one_or_none.return_value = inv

    resp = client.post(f"/payments/chase/{INVOICE_ID}", headers=auth_headers)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invoice already paid"


def test_chase_invoice_returns_link(client, auth_headers, mock_db):
    inv = _make_invoice(status="pending", stripe_payment_link="https://pay.stripe.com/abc123")
    mock_db.execute.return_value.scalar_one_or_none.return_value = inv

    resp = client.post(f"/payments/chase/{INVOICE_ID}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "chase_sent"
    assert data["payment_link"] == "https://pay.stripe.com/abc123"
    assert data["invoice_id"] == INVOICE_ID


def test_chase_invalid_invoice_id(client, auth_headers, mock_db):
    resp = client.post("/payments/chase/not-a-uuid", headers=auth_headers)
    assert resp.status_code == 422
