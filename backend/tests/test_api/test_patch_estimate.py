"""Tests for PATCH /reports/{id}/estimate — pure derivation logic first, DB tests in Task 2."""


def _derive(labor_hours: float, labor_rate: float, parts_cost: float):
    """Mirror the derivation logic from the endpoint."""
    labor_cost = round(labor_hours * labor_rate, 2)
    total = round(labor_cost + parts_cost, 2)
    return labor_cost, total


def test_derive_fields():
    labor_cost, total = _derive(2.0, 125.0, 85.0)
    assert labor_cost == 250.0
    assert total == 335.0


def test_derive_zero_hours():
    labor_cost, total = _derive(0.0, 125.0, 40.0)
    assert labor_cost == 0.0
    assert total == 40.0


def test_derive_fractional_hours():
    labor_cost, total = _derive(1.5, 90.0, 22.50)
    assert labor_cost == 135.0
    assert total == 157.5


def test_derive_zero_parts():
    labor_cost, total = _derive(2.0, 100.0, 0.0)
    assert labor_cost == 200.0
    assert total == 200.0


# ── HTTP-layer tests (require FastAPI TestClient + auth) ──────────────────


def test_patch_estimate_404(client, auth_headers):
    """Non-existent report returns 404."""
    resp = client.patch(
        "/reports/00000000-0000-0000-0000-000000000000/estimate",
        json={"items": [{"part": "Oil change", "labor_hours": 1.0, "labor_rate": 90.0, "parts_cost": 22.0}]},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_patch_estimate_invalid_uuid(client, auth_headers):
    """Malformed UUID returns 404."""
    resp = client.patch(
        "/reports/not-a-uuid/estimate",
        json={"items": []},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_patch_estimate_missing_fields(client, auth_headers):
    """Missing required Pydantic fields return 422."""
    resp = client.patch(
        "/reports/00000000-0000-0000-0000-000000000000/estimate",
        json={"items": [{"part": "Oil change"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_patch_estimate_unauthenticated(client):
    """No auth token returns 401."""
    resp = client.patch(
        "/reports/00000000-0000-0000-0000-000000000000/estimate",
        json={"items": []},
    )
    assert resp.status_code == 401


def test_patch_estimate_non_owner_forbidden(client, mock_settings):
    """Non-owner role returns 403 — only owners may edit estimates."""
    import jwt
    from src.config import settings
    from datetime import datetime, timedelta, timezone
    token = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000002",
            "shop_id": "00000000-0000-0000-0000-000000000099",
            "role": "staff",
            "email": "staff@shop.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        settings.JWT_SECRET.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )
    staff_headers = {"Authorization": f"Bearer {token}"}
    resp = client.patch(
        "/reports/00000000-0000-0000-0000-000000000000/estimate",
        json={"items": []},
        headers=staff_headers,
    )
    assert resp.status_code == 403
