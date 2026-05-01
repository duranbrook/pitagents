import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock, patch

SHOP_ID = "00000000-0000-0000-0000-000000000099"
USER_ID = "00000000-0000-0000-0000-000000000001"


def _make_invoice(**kwargs) -> MagicMock:
    inv = MagicMock()
    inv.id = kwargs.get("id", uuid.uuid4())
    inv.shop_id = uuid.UUID(SHOP_ID)
    inv.job_card_id = kwargs.get("job_card_id", None)
    inv.number = kwargs.get("number", "INV-0001")
    inv.customer_id = kwargs.get("customer_id", None)
    inv.vehicle_id = kwargs.get("vehicle_id", None)
    inv.status = kwargs.get("status", "pending")
    inv.line_items = kwargs.get("line_items", [])
    inv.subtotal = kwargs.get("subtotal", Decimal("0"))
    inv.tax_rate = kwargs.get("tax_rate", Decimal("0"))
    inv.total = kwargs.get("total", Decimal("100.00"))
    inv.amount_paid = kwargs.get("amount_paid", Decimal("0"))
    inv.due_date = kwargs.get("due_date", None)
    inv.stripe_payment_link = kwargs.get("stripe_payment_link", None)
    inv.stripe_payment_intent_id = kwargs.get("stripe_payment_intent_id", None)
    inv.pdf_url = kwargs.get("pdf_url", None)
    inv.created_at = kwargs.get("created_at", datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc))
    inv.updated_at = kwargs.get("updated_at", datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc))
    return inv


def test_list_invoices_empty(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    resp = client.get("/invoices", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_invoice_manual(client, auth_headers, mock_db):
    inv = _make_invoice()
    # First execute call is _next_invoice_number (returns scalar), second is refresh-time fetch
    mock_db.execute.return_value.scalar.return_value = None  # empty table → INV-0001
    mock_db.execute.return_value.scalar_one_or_none.return_value = inv
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.refresh = AsyncMock()

    # subtotal and total are no longer accepted — computed server-side from line_items
    resp = client.post(
        "/invoices",
        json={"line_items": [], "tax_rate": 0.0},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["number"] == "INV-0001"
    assert data["status"] == "pending"


def test_create_invoice_from_job_card(client, auth_headers, mock_db):
    jc_id = uuid.uuid4()
    card = MagicMock()
    card.id = jc_id
    card.shop_id = uuid.UUID(SHOP_ID)
    card.customer_id = None
    card.vehicle_id = None
    card.services = [{"description": "Oil change", "labor_cost": 50.0}]
    card.parts = [{"name": "Oil filter", "qty": 1, "sell_price": 15.0}]

    inv = _make_invoice(
        job_card_id=jc_id,
        line_items=[
            {"description": "Oil change", "quantity": 1.0, "unit_price": 50.0, "amount": 50.0},
            {"description": "Oil filter", "quantity": 1.0, "unit_price": 15.0, "amount": 15.0},
        ],
        subtotal=Decimal("65.00"),
        total=Decimal("65.00"),
    )

    call_count = 0

    async def execute_side_effect(query, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            # Job card lookup
            result.scalar_one_or_none.return_value = card
            result.scalar.return_value = None
        elif call_count == 2:
            # Duplicate invoice check — no existing invoice
            result.scalar_one_or_none.return_value = None
            result.scalar.return_value = None
        else:
            # _next_invoice_number
            result.scalar.return_value = None
            result.scalar_one_or_none.return_value = None
        result.scalars.return_value.all.return_value = []
        return result

    mock_db.execute = AsyncMock(side_effect=execute_side_effect)
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.refresh = AsyncMock()

    resp = client.post(
        "/invoices/from-job-card",
        json={"job_card_id": str(jc_id), "tax_rate": 0.0},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["number"] == "INV-0001"


def test_get_invoice_404(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    resp = client.get(f"/invoices/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


def test_record_payment_sets_paid(client, auth_headers, mock_db):
    inv_id = uuid.uuid4()
    inv = _make_invoice(
        id=inv_id,
        total=Decimal("100.00"),
        amount_paid=Decimal("0"),
        status="pending",
    )

    event = MagicMock()
    event.id = uuid.uuid4()
    event.invoice_id = inv_id
    event.amount = Decimal("100.00")
    event.method = "cash"
    event.recorded_by = uuid.UUID(USER_ID)
    event.recorded_at = datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
    event.notes = None

    call_count = 0

    async def execute_side_effect(query, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        # First call: load invoice for record-payment
        result.scalar_one_or_none.return_value = inv
        result.scalar.return_value = None
        result.scalars.return_value.all.return_value = []
        return result

    mock_db.execute = AsyncMock(side_effect=execute_side_effect)
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    async def refresh_side_effect(obj):
        # After refresh, pretend event has its fields set
        if hasattr(obj, "invoice_id"):
            obj.id = event.id
            obj.invoice_id = event.invoice_id
            obj.amount = event.amount
            obj.method = event.method
            obj.recorded_by = event.recorded_by
            obj.recorded_at = event.recorded_at
            obj.notes = event.notes

    mock_db.refresh = AsyncMock(side_effect=refresh_side_effect)

    resp = client.post(
        f"/invoices/{inv_id}/record-payment",
        json={"amount": 100.0, "method": "cash"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["method"] == "cash"
    # Status on invoice should have been set to "paid"
    assert inv.status == "paid"


def test_record_payment_overpayment_rejected(client, auth_headers, mock_db):
    inv_id = uuid.uuid4()
    inv = _make_invoice(
        id=inv_id,
        total=Decimal("100.00"),
        amount_paid=Decimal("0"),
        status="pending",
    )

    mock_db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=inv),
        scalar=MagicMock(return_value=None),
        scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))),
    ))
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.refresh = AsyncMock()

    resp = client.post(
        f"/invoices/{inv_id}/record-payment",
        json={"amount": 150.0, "method": "cash"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "exceeds" in resp.json()["detail"].lower()


def test_update_invoice_cannot_set_paid_directly(client, auth_headers, mock_db):
    inv_id = uuid.uuid4()
    inv = _make_invoice(id=inv_id, status="pending")

    mock_db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=inv),
        scalar=MagicMock(return_value=None),
        scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))),
    ))
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.refresh = AsyncMock()

    resp = client.patch(
        f"/invoices/{inv_id}",
        json={"status": "paid"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "record-payment" in resp.json()["detail"]


def test_create_invoice_from_job_card_duplicate_rejected(client, auth_headers, mock_db):
    jc_id = uuid.uuid4()
    card = MagicMock()
    card.id = jc_id
    card.shop_id = uuid.UUID(SHOP_ID)
    card.customer_id = None
    card.vehicle_id = None
    card.services = []
    card.parts = []

    existing_inv = _make_invoice(job_card_id=jc_id)

    call_count = 0

    async def execute_side_effect(query, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            # Job card lookup
            result.scalar_one_or_none.return_value = card
            result.scalar.return_value = None
        else:
            # Duplicate invoice check — existing invoice found
            result.scalar_one_or_none.return_value = existing_inv
            result.scalar.return_value = None
        result.scalars.return_value.all.return_value = []
        return result

    mock_db.execute = AsyncMock(side_effect=execute_side_effect)
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.refresh = AsyncMock()

    resp = client.post(
        "/invoices/from-job-card",
        json={"job_card_id": str(jc_id), "tax_rate": 0.0},
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"].lower()


def test_send_payment_link_no_stripe_key(client, auth_headers, mock_db, monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    inv = _make_invoice()
    mock_db.execute.return_value.scalar_one_or_none.return_value = inv
    resp = client.post(f"/invoices/{inv.id}/payment-link", headers=auth_headers)
    assert resp.status_code == 400
    assert "Stripe not configured" in resp.json()["detail"]


def test_send_payment_link_returns_link(client, auth_headers, mock_db, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    inv = _make_invoice()
    mock_db.execute.return_value.scalar_one_or_none.return_value = inv
    mock_db.commit = AsyncMock()
    with patch("stripe.checkout.Session.create") as mock_create:
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_abc"
        mock_create.return_value = mock_session
        resp = client.post(f"/invoices/{inv.id}/payment-link", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["payment_link"] == "https://checkout.stripe.com/pay/cs_test_abc"


def test_financing_link_not_configured(client, auth_headers, mock_db):
    inv = _make_invoice(total=Decimal("500.00"))
    settings = MagicMock()
    settings.synchrony_enabled = False
    settings.synchrony_dealer_id = None

    call_count = 0

    async def execute_side_effect(query, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = inv
        else:
            result.scalar_one_or_none.return_value = settings
        result.scalar.return_value = None
        result.scalars.return_value.all.return_value = []
        return result

    mock_db.execute = AsyncMock(side_effect=execute_side_effect)
    resp = client.post(
        f"/invoices/{inv.id}/financing-link",
        json={"provider": "synchrony"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_financing_link_wisetack_configured(client, auth_headers, mock_db):
    inv = _make_invoice(total=Decimal("600.00"))
    settings = MagicMock()
    settings.wisetack_enabled = True
    settings.wisetack_merchant_id = "merchant-123"

    call_count = 0

    async def execute_side_effect(query, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = inv
        else:
            result.scalar_one_or_none.return_value = settings
        result.scalar.return_value = None
        result.scalars.return_value.all.return_value = []
        return result

    mock_db.execute = AsyncMock(side_effect=execute_side_effect)
    resp = client.post(
        f"/invoices/{inv.id}/financing-link",
        json={"provider": "wisetack"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "wisetack"
    assert "merchant-123" in data["application_link"]


def test_financing_link_unknown_provider(client, auth_headers, mock_db):
    inv = _make_invoice(total=Decimal("300.00"))
    settings = MagicMock()

    call_count = 0

    async def execute_side_effect(query, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = inv
        else:
            result.scalar_one_or_none.return_value = settings
        result.scalar.return_value = None
        result.scalars.return_value.all.return_value = []
        return result

    mock_db.execute = AsyncMock(side_effect=execute_side_effect)
    resp = client.post(
        f"/invoices/{inv.id}/financing-link",
        json={"provider": "unknown_provider"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "Unknown provider" in resp.json()["detail"]
