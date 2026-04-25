import uuid
from src.models.customer_message import CustomerMessage
from src.models.report import Report
from src.models.chat_message import ChatMessage


def test_customer_message_columns():
    vehicle_id = uuid.uuid4()
    cm = CustomerMessage(
        vehicle_id=vehicle_id,
        direction="out",
        channel="wa",
        body="Your car is ready!",
    )
    assert cm.vehicle_id == vehicle_id
    assert cm.direction == "out"
    assert cm.channel == "wa"
    assert cm.body == "Your car is ready!"
    assert cm.report_id is None
    assert cm.external_id is None
    assert cm.sent_at is None


def test_customer_message_auto_id():
    cm = CustomerMessage(vehicle_id=uuid.uuid4(), direction="in", channel="email", body="Thanks")
    assert cm.id is not None


def test_report_has_vehicle_id_column():
    col_names = [c.name for c in Report.__table__.columns]
    assert "vehicle_id" in col_names


def test_report_has_title_column():
    col_names = [c.name for c in Report.__table__.columns]
    assert "title" in col_names


def test_report_has_status_column():
    col_names = [c.name for c in Report.__table__.columns]
    assert "status" in col_names


def test_chat_message_has_vehicle_id_column():
    col_names = [c.name for c in ChatMessage.__table__.columns]
    assert "vehicle_id" in col_names
