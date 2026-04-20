import uuid
from sqlalchemy import Column, String, Numeric, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from src.db.base import Base


class Shop(Base):
    __tablename__ = "shops"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    address = Column(String(500), nullable=True)
    labor_rate = Column(Numeric(8, 2), default=120.00)
    pricing_flag = Column(
        SAEnum("alldata", "shop", name="pricing_source_enum"),
        default="shop",
        nullable=False,
    )
    alldata_api_key = Column(String(255), nullable=True)
