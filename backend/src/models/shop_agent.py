import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from src.db.base import Base


class ShopAgent(Base):
    __tablename__ = "shop_agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String, nullable=False)
    role_tagline = Column(String, nullable=False)
    accent_color = Column(String(20), nullable=False, default="#d97706")
    initials = Column(String(3), nullable=False)
    system_prompt = Column(String, nullable=False)
    tools = Column(JSON, nullable=False, default=list)
    sort_order = Column(Integer, nullable=False, default=0)
    persona_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("created_at", datetime.now(timezone.utc))
        super().__init__(**kwargs)
