import uuid
from sqlalchemy import Column, String, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # nullable for Google OAuth users
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    role = Column(
        SAEnum("owner", "technician", name="user_role_enum"),
        nullable=False,
    )
    name = Column(String(255), nullable=True)
    preferences = Column(JSONB, nullable=False, server_default="{}")
