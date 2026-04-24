import uuid
from datetime import datetime
from sqlalchemy import Column, Numeric, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from src.db.base import Base


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("inspection_sessions.id", ondelete="SET NULL"), nullable=True)
    status = Column(
        SAEnum("draft", "final", "sent", name="quote_status"),
        default="draft",
        server_default="draft",
        nullable=False,
    )
    line_items = Column(JSONB, default=list, server_default="'[]'::jsonb")
    total = Column(Numeric(10, 2), default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow, nullable=True)
