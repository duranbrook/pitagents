import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base


class JobCardColumn(Base):
    __tablename__ = "job_card_columns"

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
