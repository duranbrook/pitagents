import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, UniqueConstraint, Numeric, JSON, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("shop_id", "number", name="uq_invoices_shop_number"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(
        UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    job_card_id = Column(
        UUID(as_uuid=True), ForeignKey("job_cards.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    number = Column(String(20), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), default="pending", nullable=False)
    line_items = Column(JSON, default=list)
    subtotal = Column(Numeric(10, 2), default=0)
    tax_rate = Column(Numeric(5, 4), default=0)
    total = Column(Numeric(10, 2), default=0)
    amount_paid = Column(Numeric(10, 2), default=0)
    due_date = Column(Date, nullable=True)
    stripe_payment_link = Column(String(500), nullable=True)
    stripe_payment_intent_id = Column(String(200), nullable=True)
    pdf_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)


class InvoicePaymentEvent(Base):
    __tablename__ = "invoice_payment_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    amount = Column(Numeric(10, 2), nullable=False)
    method = Column(String(50), nullable=False)  # stripe|card|cash|check
    recorded_by = Column(UUID(as_uuid=True), nullable=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(String(500), nullable=True)

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
