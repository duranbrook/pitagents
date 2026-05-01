import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

SHOP_ID = "00000000-0000-0000-0000-000000000099"


def _make_config(**kwargs) -> MagicMock:
    cfg = MagicMock()
    cfg.id = kwargs.get("id", uuid.uuid4())
    cfg.shop_id = uuid.UUID(SHOP_ID)
    cfg.service_type = kwargs.get("service_type", "Oil Change")
    cfg.window_start_months = kwargs.get("window_start_months", 3)
    cfg.window_end_months = kwargs.get("window_end_months", 6)
    cfg.sms_enabled = kwargs.get("sms_enabled", True)
    cfg.email_enabled = kwargs.get("email_enabled", True)
    cfg.message_template = kwargs.get("message_template", "Hi {first_name}")
    cfg.created_at = kwargs.get("created_at", datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc))
    return cfg


def test_list_reminder_configs_empty(client, auth_headers, mock_db):
    """When no configs exist, seeding starts but for the test we short-circuit
    by having execute always return empty (no rows); the route adds seeds and
    commits — we just verify it returns a list (seeded items won't have proper
    UUIDs from refresh in mock, but the route will return whatever refresh gives).
    For a pure empty-return test, mock refresh to be a no-op and scalars to
    return [] both times (before seed and during any re-query)."""

    # All executes return empty; refresh is no-op
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.refresh = AsyncMock()

    resp = client.get("/reminders/config", headers=auth_headers)
    # Seeding inserts 4 defaults and refreshes them — mock refresh is no-op so
    # _cfg_to_response runs on the real ServiceReminderConfig objects.
    # The response list should have 4 entries (the seeded defaults).
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # Seeded 4 defaults
    assert len(data) == 4


def test_create_reminder_config(client, auth_headers, mock_db):
    cfg = _make_config(service_type="Brake Check", window_start_months=12, window_end_months=18)
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    async def refresh_side_effect(obj):
        obj.id = cfg.id
        obj.shop_id = cfg.shop_id
        obj.service_type = cfg.service_type
        obj.window_start_months = cfg.window_start_months
        obj.window_end_months = cfg.window_end_months
        obj.sms_enabled = cfg.sms_enabled
        obj.email_enabled = cfg.email_enabled
        obj.message_template = cfg.message_template
        obj.created_at = cfg.created_at

    mock_db.refresh = AsyncMock(side_effect=refresh_side_effect)

    resp = client.post(
        "/reminders/config",
        json={
            "service_type": "Brake Check",
            "window_start_months": 12,
            "window_end_months": 18,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["service_type"] == "Brake Check"
    assert data["window_start_months"] == 12


def test_run_reminder_job(client, auth_headers, mock_db):
    """POST /reminders/run with empty reminder list returns reminders_sent: 0."""
    mock_db.execute.return_value.all.return_value = []
    mock_db.commit = AsyncMock()

    resp = client.post("/reminders/run", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"reminders_sent": 0}
