import uuid
from sqlalchemy import Column, String, Boolean, JSON, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base


class ShopSettings(Base):
    __tablename__ = "shop_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(
        UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    nav_pins = Column(JSON, default=list)
    stripe_publishable_key = Column(String(200), nullable=True)
    stripe_secret_key_encrypted = Column(Text, nullable=True)
    mitchell1_enabled = Column(Boolean, default=False)
    mitchell1_api_key_encrypted = Column(Text, nullable=True)
    synchrony_enabled = Column(Boolean, default=False)
    synchrony_dealer_id = Column(String(100), nullable=True)
    wisetack_enabled = Column(Boolean, default=False)
    wisetack_merchant_id = Column(String(100), nullable=True)
    quickbooks_enabled = Column(Boolean, default=False)
    quickbooks_refresh_token_encrypted = Column(Text, nullable=True)
    carmd_api_key = Column(String, nullable=True)
    carmd_partner_token = Column(String, nullable=True)
    financing_threshold = Column(String(10), default="500")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
