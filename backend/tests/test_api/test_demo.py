def test_submit_demo_request(client, mock_db):
    """Valid demo request returns ok: true."""
    resp = client.post("/demo/request", json={
        "first_name": "Marcus",
        "last_name": "Thompson",
        "email": "marcus@cityauto.com",
        "shop_name": "City Auto Center",
        "locations": "1 location",
        "message": "Looking forward to the demo.",
    })
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()


def test_submit_demo_request_no_message(client):
    """Message field is optional."""
    resp = client.post("/demo/request", json={
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane@shop.com",
        "shop_name": "Jane's Auto",
        "locations": "2–5 locations",
    })
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_submit_demo_request_missing_field(client):
    """Missing required field returns 422."""
    resp = client.post("/demo/request", json={
        "first_name": "Marcus",
        # missing last_name, email, shop_name, locations
    })
    assert resp.status_code == 422
