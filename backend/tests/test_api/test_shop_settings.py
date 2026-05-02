import uuid
from decimal import Decimal
from unittest.mock import MagicMock

SHOP_ID = "00000000-0000-0000-0000-000000000099"


def _make_settings(**overrides):
    s = MagicMock()
    s.id = uuid.uuid4()
    s.shop_id = uuid.UUID(SHOP_ID)
    s.nav_pins = []
    s.stripe_publishable_key = None
    s.stripe_secret_key_encrypted = None
    s.mitchell1_enabled = False
    s.mitchell1_api_key_encrypted = None
    s.synchrony_enabled = False
    s.synchrony_dealer_id = None
    s.wisetack_enabled = False
    s.wisetack_merchant_id = None
    s.quickbooks_enabled = False
    s.quickbooks_refresh_token_encrypted = None
    s.carmd_api_key = None
    s.financing_threshold = "500"
    for k, v in overrides.items():
        setattr(s, k, v)
    return s


def _make_shop(**overrides):
    shop = MagicMock()
    shop.id = uuid.UUID(SHOP_ID)
    shop.name = "Test Shop"
    shop.address = "123 Main St"
    shop.labor_rate = Decimal("120.00")
    for k, v in overrides.items():
        setattr(shop, k, v)
    return shop


def test_get_shop_settings_returns_defaults(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    resp = client.get("/settings/shop", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["nav_pins"] == []
    assert data["mitchell1_enabled"] is False
    assert data["financing_threshold"] == "500"


def test_patch_shop_settings_updates_nav_pins(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = _make_settings()
    resp = client.patch(
        "/settings/shop",
        json={"nav_pins": ["/job-cards", "/invoices"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200


def test_get_shop_profile(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = _make_shop()
    resp = client.get("/settings/profile", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Shop"
    assert data["address"] == "123 Main St"
    assert data["labor_rate"] == "120.00"


def test_get_shop_profile_not_found(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    resp = client.get("/settings/profile", headers=auth_headers)
    assert resp.status_code == 404


def test_patch_shop_profile(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = _make_shop(
        name="Updated Shop", labor_rate=Decimal("150.00")
    )
    resp = client.patch(
        "/settings/profile",
        json={"name": "Updated Shop", "labor_rate": "150.00"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Shop"
    assert data["labor_rate"] == "150.00"


def test_patch_shop_profile_not_found(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    resp = client.patch("/settings/profile", json={"name": "X"}, headers=auth_headers)
    assert resp.status_code == 404


def test_patch_shop_profile_invalid_labor_rate(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = _make_shop()
    resp = client.patch(
        "/settings/profile",
        json={"labor_rate": "not-a-number"},
        headers=auth_headers,
    )
    assert resp.status_code == 422
