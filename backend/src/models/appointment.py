import uuid
from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True)
    starts_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ends_at = Column(DateTime(timezone=True), nullable=False)
    service_requested = Column(String(500), nullable=True)
    status = Column(String(20), default="pending", nullable=False)  # pending|confirmed|cancelled
    notes = Column(Text, nullable=True)
    source = Column(String(20), default="manual", nullable=False)  # manual|booking_link
    booking_token = Column(String(100), nullable=True, unique=True)
    job_card_id = Column(UUID(as_uuid=True), ForeignKey("job_cards.id", ondelete="SET NULL"), nullable=True)
    customer_name = Column(String(255), nullable=True)
    customer_phone = Column(String(50), nullable=True)
    customer_email = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)


class BookingConfig(Base):
    __tablename__ = "booking_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    slug = Column(String(100), nullable=False, unique=True)
    available_services = Column(String, default="[]")  # JSON as text
    working_hours_start = Column(String(5), default="08:00")
    working_hours_end = Column(String(5), default="17:00")
    slot_duration_minutes = Column(String(5), default="60")
    working_days = Column(String, default="[1,2,3,4,5]")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
