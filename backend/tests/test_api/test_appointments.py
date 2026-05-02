import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

SHOP_ID = "00000000-0000-0000-0000-000000000099"

STARTS_AT = "2026-06-01T09:00:00+00:00"
ENDS_AT = "2026-06-01T10:00:00+00:00"


def _make_appt(**kwargs) -> MagicMock:
    appt = MagicMock()
    appt.id = kwargs.get("id", uuid.uuid4())
    appt.shop_id = uuid.UUID(SHOP_ID)
    appt.customer_id = kwargs.get("customer_id", None)
    appt.vehicle_id = kwargs.get("vehicle_id", None)
    appt.starts_at = kwargs.get(
        "starts_at", datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc)
    )
    appt.ends_at = kwargs.get(
        "ends_at", datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
    )
    appt.service_requested = kwargs.get("service_requested", "Oil change")
    appt.status = kwargs.get("status", "pending")
    appt.notes = kwargs.get("notes", None)
    appt.source = kwargs.get("source", "manual")
    appt.booking_token = kwargs.get("booking_token", None)
    appt.job_card_id = kwargs.get("job_card_id", None)
    appt.customer_name = kwargs.get("customer_name", None)
    appt.customer_phone = kwargs.get("customer_phone", None)
    appt.customer_email = kwargs.get("customer_email", None)
    appt.created_at = kwargs.get("created_at", datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc))
    return appt


def test_list_appointments_empty(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    resp = client.get("/appointments", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_appointment(client, auth_headers, mock_db):
    appt = _make_appt()
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.refresh = AsyncMock()
    # refresh doesn't replace the object; the route calls _appt_to_response(appt)
    # so we need to return the mock appt via scalar_one_or_none after refresh
    # Actually refresh is a no-op on the mock — the route passes `appt` directly
    resp = client.post(
        "/appointments",
        json={
            "starts_at": STARTS_AT,
            "ends_at": ENDS_AT,
            "service_requested": "Oil change",
            "status": "pending",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    # The mock refresh doesn't populate fields, so we just check structure
    assert "id" in data
    assert "shop_id" in data
    assert data["status"] == "pending"


def test_get_appointment_404(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    resp = client.get(f"/appointments/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


def test_convert_to_job_card(client, auth_headers, mock_db):
    appt_id = uuid.uuid4()
    jc_id = uuid.uuid4()

    appt = _make_appt(id=appt_id)
    card = MagicMock()
    card.id = jc_id
    card.number = "JC-0001"

    call_count = 0

    async def execute_side_effect(query, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            # Appointment lookup
            result.scalar_one_or_none.return_value = appt
            result.scalar.return_value = None
        elif call_count == 2:
            # MAX job card number
            result.scalar.return_value = None
            result.scalar_one_or_none.return_value = None
        else:
            result.scalar.return_value = None
            result.scalar_one_or_none.return_value = None
        result.scalars.return_value.all.return_value = []
        return result

    mock_db.execute = AsyncMock(side_effect=execute_side_effect)
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    async def refresh_side_effect(obj):
        if hasattr(obj, "number"):
            obj.id = jc_id
            obj.number = "JC-0001"

    mock_db.refresh = AsyncMock(side_effect=refresh_side_effect)

    resp = client.post(
        f"/appointments/{appt_id}/convert-to-job-card",
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "job_card_id" in data
    assert data["number"] == "JC-0001"


def test_get_my_booking_config(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    import uuid
    cfg = MagicMock()
    cfg.id = uuid.uuid4()
    cfg.shop_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
    cfg.slug = "test-shop"
    cfg.available_services = "[]"
    cfg.working_hours_start = "08:00"
    cfg.working_hours_end = "17:00"
    cfg.slot_duration_minutes = "60"
    cfg.working_days = "[1,2,3,4,5]"
    cfg.created_at = None
    mock_db.execute.return_value.scalar_one_or_none.return_value = cfg
    resp = client.get("/appointments/my-config", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "test-shop"
    assert data["working_hours_start"] == "08:00"
    assert data["working_hours_end"] == "17:00"
    assert data["slot_duration_minutes"] == "60"


def test_get_my_booking_config_not_found(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    resp = client.get("/appointments/my-config", headers=auth_headers)
    assert resp.status_code == 404


def test_patch_my_booking_config(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    import uuid
    cfg = MagicMock()
    cfg.id = uuid.uuid4()
    cfg.shop_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
    cfg.slug = "test-shop"
    cfg.available_services = "[]"
    cfg.working_hours_start = "09:00"
    cfg.working_hours_end = "18:00"
    cfg.slot_duration_minutes = "30"
    cfg.working_days = "[1,2,3,4,5]"
    cfg.created_at = None
    mock_db.execute.return_value.scalar_one_or_none.return_value = cfg
    resp = client.patch(
        "/appointments/my-config",
        json={"working_hours_start": "09:00", "slot_duration_minutes": "30"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "test-shop"
