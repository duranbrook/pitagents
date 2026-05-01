import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from src.api.main import app


def test_list_campaigns_empty(client, auth_headers, mock_db):
    resp = client.get("/marketing/campaigns", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_templates(client, auth_headers):
    resp = client.get("/marketing/templates", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 3
    ids = [t["id"] for t in body]
    assert "seasonal-promo" in ids
    assert "win-back" in ids
    assert "maintenance-reminder" in ids


def test_create_campaign(client, auth_headers, mock_db):
    campaign_id = uuid.uuid4()
    mock_campaign = MagicMock()
    mock_campaign.id = campaign_id
    mock_campaign.shop_id = "00000000-0000-0000-0000-000000000099"
    mock_campaign.name = "Test Campaign"
    mock_campaign.status = "draft"
    mock_campaign.message_body = "Hi {first_name}, come in for an oil change!"
    mock_campaign.channel = "sms"
    mock_campaign.audience_segment = {"type": "all_customers"}
    mock_campaign.send_at = None
    mock_campaign.sent_at = None
    mock_campaign.stats = {}
    from datetime import datetime
    mock_campaign.created_at = datetime(2026, 5, 1, 10, 0, 0)

    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=lambda obj: None)

    # After refresh the campaign object should be populated — mock refresh to set attrs
    async def _refresh(obj):
        obj.id = campaign_id
        obj.shop_id = "00000000-0000-0000-0000-000000000099"
        obj.name = "Test Campaign"
        obj.status = "draft"
        obj.message_body = "Hi {first_name}, come in for an oil change!"
        obj.channel = "sms"
        obj.audience_segment = {"type": "all_customers"}
        obj.send_at = None
        obj.sent_at = None
        obj.stats = {}
        obj.created_at = datetime(2026, 5, 1, 10, 0, 0)

    mock_db.refresh = _refresh

    resp = client.post(
        "/marketing/campaigns",
        json={
            "name": "Test Campaign",
            "message_body": "Hi {first_name}, come in for an oil change!",
            "channel": "sms",
            "audience_segment": {"type": "all_customers"},
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Test Campaign"
    assert body["status"] == "draft"
    assert body["channel"] == "sms"
