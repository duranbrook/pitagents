import os
import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_autoshop")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")

from src.api.main import app
from src.api.auth import create_access_token
from src.db.base import engine

SHOP_ID = "00000000-0000-0000-0000-000000000099"


def _auth_headers() -> dict:
    token = create_access_token({
        "sub": "00000000-0000-0000-0000-000000000001",
        "shop_id": SHOP_ID,
        "role": "owner",
    })
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(autouse=True)
async def reset_engine():
    await engine.dispose()
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def vehicle_id(client):
    cust = await client.post(
        "/customers",
        json={"name": "Msg Customer", "phone": "+15559876543", "email": "msg@example.com"},
        headers=_auth_headers(),
    )
    customer_id = cust.json()["customer_id"]
    veh = await client.post(
        f"/customers/{customer_id}/vehicles",
        json={"year": 2021, "make": "Honda", "model": "Civic"},
        headers=_auth_headers(),
    )
    return veh.json()["vehicle_id"]


@pytest.mark.asyncio
async def test_send_whatsapp_message(client, vehicle_id):
    mock_msg = MagicMock()
    mock_msg.sid = "SM_test_sid_12345"
    with patch("src.api.customer_messages.TwilioClient") as MockTwilio:
        MockTwilio.return_value.messages.create.return_value = mock_msg
        resp = await client.post(
            f"/vehicles/{vehicle_id}/messages",
            json={"body": "Your car is ready!", "channel": "wa"},
            headers=_auth_headers(),
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["direction"] == "out"
    assert data["channel"] == "wa"
    assert data["body"] == "Your car is ready!"
    assert data["external_id"] == "SM_test_sid_12345"
    assert data["sent_at"] is not None
    assert "message_id" in data


@pytest.mark.asyncio
async def test_send_email_message(client, vehicle_id):
    mock_resp = MagicMock()
    mock_resp.headers = {"X-Message-Id": "sg_test_id_789"}
    with patch("src.api.customer_messages.SendGridClient") as MockSG:
        MockSG.return_value.send.return_value = mock_resp
        resp = await client.post(
            f"/vehicles/{vehicle_id}/messages",
            json={"body": "Here is your estimate.", "channel": "email", "subject": "Estimate Ready"},
            headers=_auth_headers(),
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["channel"] == "email"
    assert data["external_id"] == "sg_test_id_789"


@pytest.mark.asyncio
async def test_list_messages_returns_thread(client, vehicle_id):
    mock_msg = MagicMock()
    mock_msg.sid = "SM_list_test_001"
    with patch("src.api.customer_messages.TwilioClient") as MockTwilio:
        MockTwilio.return_value.messages.create.return_value = mock_msg
        await client.post(
            f"/vehicles/{vehicle_id}/messages",
            json={"body": "Thread message", "channel": "wa"},
            headers=_auth_headers(),
        )
    resp = await client.get(f"/vehicles/{vehicle_id}/messages", headers=_auth_headers())
    assert resp.status_code == 200
    messages = resp.json()
    assert isinstance(messages, list)
    assert any(m["body"] == "Thread message" for m in messages)


@pytest.mark.asyncio
async def test_send_message_invalid_channel(client, vehicle_id):
    resp = await client.post(
        f"/vehicles/{vehicle_id}/messages",
        json={"body": "test", "channel": "sms"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_send_message_requires_auth(client, vehicle_id):
    resp = await client.post(
        f"/vehicles/{vehicle_id}/messages",
        json={"body": "test", "channel": "wa"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_twilio_webhook_creates_inbound_message(client):
    import uuid as _uuid
    phone = f"+1555{str(_uuid.uuid4().int)[:7]}"
    cust = await client.post(
        "/customers",
        json={"name": "Webhook Test", "phone": phone},
        headers=_auth_headers(),
    )
    customer_id = cust.json()["customer_id"]
    veh = await client.post(
        f"/customers/{customer_id}/vehicles",
        json={"year": 2023, "make": "Test", "model": "Webhook"},
        headers=_auth_headers(),
    )
    vehicle_id = veh.json()["vehicle_id"]

    with patch("src.api.customer_messages.RequestValidator") as MockValidator:
        MockValidator.return_value.validate.return_value = True
        resp = await client.post(
            "/twilio/webhook",
            data={
                "From": f"whatsapp:{phone}",
                "To": "whatsapp:+14155238886",
                "Body": "I'll pick it up at 5!",
                "MessageSid": "SM_inbound_001",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    thread = await client.get(f"/vehicles/{vehicle_id}/messages", headers=_auth_headers())
    assert any(
        m["direction"] == "in" and m["body"] == "I'll pick it up at 5!"
        for m in thread.json()
    )


@pytest.mark.asyncio
async def test_twilio_webhook_unknown_sender_returns_ignored(client):
    with patch("src.api.customer_messages.RequestValidator") as MockValidator:
        MockValidator.return_value.validate.return_value = True
        resp = await client.post(
            "/twilio/webhook",
            data={
                "From": "whatsapp:+19991112222",
                "To": "whatsapp:+14155238886",
                "Body": "Hello?",
                "MessageSid": "SM_unknown_001",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


@pytest.mark.asyncio
async def test_twilio_webhook_invalid_signature_returns_403(client):
    resp = await client.post(
        "/twilio/webhook",
        data={
            "From": "whatsapp:+15559876543",
            "To": "whatsapp:+14155238886",
            "Body": "test",
            "MessageSid": "SM_bad_sig",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 403
