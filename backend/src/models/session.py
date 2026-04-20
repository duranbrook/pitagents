import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, JSON, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base


class InspectionSession(Base):
    __tablename__ = "inspection_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False, index=True)
    technician_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(
        SAEnum("recording", "processing", "complete", "failed", name="session_status_enum"),
        default="recording",
        nullable=False,
    )
    vehicle = Column(JSON, default=dict)
    transcript = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
