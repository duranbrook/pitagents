import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, JSON, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("inspection_sessions.id"), nullable=False)
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    summary = Column(String, nullable=True)
    title = Column(String(255), nullable=True)
    status = Column(String(10), nullable=False, default="draft", server_default="draft")
    findings = Column(JSON, default=list)
    estimate = Column(JSON, nullable=True)
    estimate_total = Column(Numeric(10, 2), default=0)
    vehicle = Column(JSON, nullable=True)
    share_token = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, index=True)
    share_expires_at = Column(DateTime(timezone=True), nullable=True)
    sent_to = Column(JSON, default=dict)
    pdf_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
