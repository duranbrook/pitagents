import uuid
from sqlalchemy import Column, String, SmallInteger, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    year = Column(SmallInteger(), nullable=False)
    make = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    trim = Column(String(100), nullable=True)
    vin = Column(String(17), nullable=True, unique=True)
    color = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
