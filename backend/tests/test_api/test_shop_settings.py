def test_get_shop_settings_returns_defaults(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    resp = client.get("/settings/shop", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["nav_pins"] == []
    assert data["mitchell1_enabled"] is False
    assert data["financing_threshold"] == "500"


def test_patch_shop_settings_updates_nav_pins(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    import uuid
    fake = MagicMock()
    fake.id = uuid.uuid4()
    fake.shop_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
    fake.nav_pins = []
    fake.stripe_publishable_key = None
    fake.stripe_secret_key_encrypted = None
    fake.mitchell1_enabled = False
    fake.mitchell1_api_key_encrypted = None
    fake.synchrony_enabled = False
    fake.synchrony_dealer_id = None
    fake.wisetack_enabled = False
    fake.wisetack_merchant_id = None
    fake.quickbooks_enabled = False
    fake.quickbooks_refresh_token_encrypted = None
    fake.carmd_api_key = None
    fake.financing_threshold = "500"
    mock_db.execute.return_value.scalar_one_or_none.return_value = fake
    resp = client.patch(
        "/settings/shop",
        json={"nav_pins": ["/job-cards", "/invoices"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200


def test_get_shop_profile(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    import uuid
    from decimal import Decimal
    shop = MagicMock()
    shop.id = uuid.UUID("00000000-0000-0000-0000-000000000099")
    shop.name = "Test Shop"
    shop.address = "123 Main St"
    shop.labor_rate = Decimal("120.00")
    mock_db.execute.return_value.scalar_one_or_none.return_value = shop
    resp = client.get("/settings/profile", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Shop"
    assert data["address"] == "123 Main St"
    assert data["labor_rate"] == "120.00"


def test_patch_shop_profile(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    import uuid
    from decimal import Decimal
    shop = MagicMock()
    shop.id = uuid.UUID("00000000-0000-0000-0000-000000000099")
    shop.name = "Updated Shop"
    shop.address = "456 Oak Ave"
    shop.labor_rate = Decimal("150.00")
    mock_db.execute.return_value.scalar_one_or_none.return_value = shop
    resp = client.patch(
        "/settings/profile",
        json={"name": "Updated Shop", "labor_rate": "150.00"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Shop"
