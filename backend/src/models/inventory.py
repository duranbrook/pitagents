import uuid
from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base

VALID_CATEGORIES = ["Oils", "Brakes", "Tires", "Filters", "Electrical", "Misc"]


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(
        UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name = Column(String(255), nullable=False)
    sku = Column(String(100), nullable=True)
    category = Column(String(50), nullable=False, default="Misc")
    quantity = Column(Integer, default=0, nullable=False)
    reorder_at = Column(Integer, default=0, nullable=False)
    cost_price = Column(Numeric(10, 2), default=0)
    sell_price = Column(Numeric(10, 2), default=0)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
