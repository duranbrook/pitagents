import uuid
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from src.db.base import Base


class DemoRequest(Base):
    __tablename__ = "demo_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    shop_name = Column(String(255), nullable=False)
    locations = Column(String(50), nullable=False)
    message = Column(String(2000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
