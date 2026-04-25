import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.db.base import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    agent_id = Column(String(50), nullable=False)      # "assistant" | "tom"
    role = Column(String(20), nullable=False)           # "user" | "assistant"
    # Full Anthropic content block list, e.g. [{"type":"text","text":"..."}]
    content = Column(JSONB, nullable=False)
    # Filled only on assistant messages: [{"name":"lookup_vin","input":{...},"output":{...}}]
    tool_calls = Column(JSONB, nullable=True)
    rating = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
