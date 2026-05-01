import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

SHOP_ID = "00000000-0000-0000-0000-000000000099"
USER_ID = "00000000-0000-0000-0000-000000000001"


def _make_entry(**kwargs) -> MagicMock:
    entry = MagicMock()
    entry.id = kwargs.get("id", uuid.uuid4())
    entry.shop_id = uuid.UUID(SHOP_ID)
    entry.user_id = uuid.UUID(USER_ID)
    entry.job_card_id = kwargs.get("job_card_id", None)
    entry.task_type = kwargs.get("task_type", "Repair")
    entry.started_at = kwargs.get("started_at", datetime(2026, 5, 1, 9, 0, 0, tzinfo=timezone.utc))
    entry.ended_at = kwargs.get("ended_at", None)
    entry.duration_minutes = kwargs.get("duration_minutes", None)
    entry.notes = kwargs.get("notes", None)
    entry.qb_synced = kwargs.get("qb_synced", False)
    entry.created_at = kwargs.get("created_at", datetime(2026, 5, 1, 9, 0, 0, tzinfo=timezone.utc))
    return entry


def test_list_time_entries_empty(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    resp = client.get("/time-entries", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_clock_in_creates_entry(client, auth_headers, mock_db):
    # First execute: check for existing open entry → None (not clocked in)
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    resp = client.post(
        "/time-entries/clock-in",
        json={"task_type": "Diagnosis", "notes": "Checking brakes"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert "shop_id" in data
    assert "user_id" in data
    assert data["task_type"] == "Diagnosis"
    assert data["notes"] == "Checking brakes"
    assert data["ended_at"] is None
    assert data["duration_minutes"] is None


def test_clock_out_sets_end_time(client, auth_headers, mock_db):
    entry_id = uuid.uuid4()
    entry = _make_entry(
        id=entry_id,
        task_type="Repair",
        started_at=datetime(2026, 5, 1, 9, 0, 0, tzinfo=timezone.utc),
        ended_at=None,
    )

    mock_db.execute.return_value.scalar_one_or_none.return_value = entry
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    resp = client.post(f"/time-entries/{entry_id}/clock-out", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(entry_id)
    assert data["ended_at"] is not None
    assert data["duration_minutes"] is not None


def test_clock_out_not_found(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    random_id = str(uuid.uuid4())
    resp = client.post(f"/time-entries/{random_id}/clock-out", headers=auth_headers)
    assert resp.status_code == 404


def test_clock_in_already_clocked_in(client, auth_headers, mock_db):
    existing = _make_entry()
    mock_db.execute.return_value.scalar_one_or_none.return_value = existing

    resp = client.post(
        "/time-entries/clock-in",
        json={"task_type": "Repair"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "Already clocked in" in resp.json()["detail"]


def test_get_active_entries(client, auth_headers, mock_db):
    entry = _make_entry(ended_at=None)
    mock_db.execute.return_value.scalars.return_value.all.return_value = [entry]
    resp = client.get("/time-entries/active", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["ended_at"] is None
