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
    fake.mitchell1_enabled = False
    fake.synchrony_enabled = False
    fake.wisetack_enabled = False
    fake.quickbooks_enabled = False
    fake.financing_threshold = "500"
    mock_db.execute.return_value.scalar_one_or_none.return_value = fake
    resp = client.patch(
        "/settings/shop",
        json={"nav_pins": ["/job-cards", "/invoices"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
