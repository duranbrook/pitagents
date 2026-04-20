import uuid
from sqlalchemy import Column, String, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from src.db.base import Base


class MediaFile(Base):
    __tablename__ = "media_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("inspection_sessions.id"), nullable=False, index=True)
    media_type = Column(
        SAEnum("photo", "video", "audio", name="media_type_enum"),
        name="type",
        nullable=False,
    )
    tag = Column(
        SAEnum("vin", "odometer", "tire", "damage", "general", name="media_tag_enum"),
        default="general",
        nullable=False,
    )
    s3_url = Column(String, nullable=False)
    filename = Column(String(255), nullable=True)
