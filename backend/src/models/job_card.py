import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, UniqueConstraint, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base


class JobCardColumn(Base):
    __tablename__ = "job_card_columns"
    __table_args__ = (
        UniqueConstraint("shop_id", "position", name="uq_job_card_columns_shop_position"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(
        UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name = Column(String(100), nullable=False)
    position = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)


class JobCard(Base):
    __tablename__ = "job_cards"
    __table_args__ = (
        UniqueConstraint("shop_id", "number", name="uq_job_cards_shop_number"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(
        UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    number = Column(String(20), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True, index=True)
    column_id = Column(UUID(as_uuid=True), ForeignKey("job_card_columns.id", ondelete="SET NULL"), nullable=True)
    technician_ids = Column(JSON, default=list)
    services = Column(JSON, default=list)
    parts = Column(JSON, default=list)
    notes = Column(Text, nullable=True)
    status = Column(String(20), default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
