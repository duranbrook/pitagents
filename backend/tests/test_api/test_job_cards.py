import uuid

SHOP_ID = "00000000-0000-0000-0000-000000000099"


def test_list_columns_empty(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    resp = client.get("/job-cards/columns", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_column(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    col = MagicMock()
    col.id = uuid.uuid4()
    col.shop_id = uuid.UUID(SHOP_ID)
    col.name = "Drop-Off"
    col.position = 0
    col.created_at = "2026-05-01T00:00:00+00:00"
    mock_db.execute.return_value.scalar_one_or_none.return_value = col
    resp = client.post(
        "/job-cards/columns",
        json={"name": "Drop-Off", "position": 0},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Drop-Off"
