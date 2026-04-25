import uuid
from sqlalchemy import Column, String, Text, Enum as SAEnum, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base


class CustomerMessage(Base):
    __tablename__ = "customer_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="SET NULL"),
        nullable=True,
    )
    direction = Column(SAEnum("out", "in", name="customer_message_direction", create_type=False), nullable=False)
    channel = Column(SAEnum("wa", "email", name="customer_message_channel", create_type=False), nullable=False)
    body = Column(Text(), nullable=False)
    external_id = Column(String(255), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
