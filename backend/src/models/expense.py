import uuid
from sqlalchemy import Column, String, Numeric, Boolean, ForeignKey, DateTime, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base

EXPENSE_CATEGORIES = ["Parts", "Labor", "Utilities", "Equipment", "Misc"]


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    description = Column(String(500), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    category = Column(String(50), nullable=False, default="Misc")
    vendor = Column(String(255), nullable=True)
    expense_date = Column(Date, nullable=False)
    invoice_id = Column(UUID(as_uuid=True), nullable=True)
    qb_synced = Column(Boolean, nullable=False, default=False)
    qb_expense_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
