import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from src.db.base import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="draft")  # draft/scheduled/active/sent
    message_body = Column(String, nullable=False)
    channel = Column(String, nullable=False, default="sms")  # sms/email/both
    audience_segment = Column(JSON, nullable=False, default=dict)
    send_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    stats = Column(JSON, nullable=False, default=dict)  # sent_count, opened_count, booked_count
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("status", "draft")
        kwargs.setdefault("channel", "sms")
        kwargs.setdefault("audience_segment", {})
        kwargs.setdefault("stats", {})
        kwargs.setdefault("created_at", datetime.now(timezone.utc))
        super().__init__(**kwargs)
