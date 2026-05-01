import uuid
import sqlalchemy as sa
from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base


DEFAULT_CONFIGS = [
    {
        "service_type": "Oil Change",
        "window_start_months": 3,
        "window_end_months": 6,
        "message_template": (
            "Hi {first_name}, your {vehicle} is due for an oil change. "
            "Book now: {booking_link}"
        ),
    },
    {
        "service_type": "Tire Rotation",
        "window_start_months": 6,
        "window_end_months": 12,
        "message_template": (
            "Hi {first_name}, time for a tire rotation on your {vehicle}. "
            "Book now: {booking_link}"
        ),
    },
    {
        "service_type": "Full Service",
        "window_start_months": 10,
        "window_end_months": 14,
        "message_template": (
            "Hi {first_name}, your {vehicle} is due for a full service. "
            "Book now: {booking_link}"
        ),
    },
    {
        "service_type": "AC Check",
        "window_start_months": 10,
        "window_end_months": 14,
        "message_template": (
            "Hi {first_name}, time to check the AC on your {vehicle}. "
            "Book now: {booking_link}"
        ),
    },
]


class ServiceReminderConfig(Base):
    __tablename__ = "service_reminder_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(
        UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    service_type = Column(String(100), nullable=False)
    window_start_months = Column(Integer, nullable=False)
    window_end_months = Column(Integer, nullable=False)
    sms_enabled = Column(Boolean, nullable=False, server_default=sa.true())
    email_enabled = Column(Boolean, nullable=False, server_default=sa.true())
    message_template = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)


class ServiceReminder(Base):
    __tablename__ = "service_reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(
        UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    customer_id = Column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    vehicle_id = Column(
        UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"),
        nullable=True,
    )
    config_id = Column(
        UUID(as_uuid=True), ForeignKey("service_reminder_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    service_type = Column(String(100), nullable=False)
    status = Column(String(20), default="active", nullable=False)  # active|booked|inactive
    last_sent_at = Column(DateTime(timezone=True), nullable=True)
    last_service_at = Column(DateTime(timezone=True), nullable=True)
    send_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
