"""Feedback endpoint — rate an assistant message thumbs up or down."""
import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from qdrant_client.models import PointStruct

from src.api.deps import get_current_user
from src.db.base import get_db
from src.models.chat_message import ChatMessage
from src.db.qdrant import qdrant, embed

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["feedback"])


class FeedbackRequest(BaseModel):
    message_id: str
    rating: int   # +1 or -1
    comment: str | None = None


@router.post("/{agent_id}/feedback", status_code=204)
async def rate_message(
    agent_id: str,
    body: FeedbackRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.rating not in (1, -1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rating must be 1 or -1")

    try:
        msg_id = uuid.UUID(body.message_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid message_id")

    user_id = uuid.UUID(current_user["sub"])
    result = await db.execute(select(ChatMessage).where(ChatMessage.id == msg_id))
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    if message.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your message")
    if message.role != "assistant":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only rate assistant messages")

    response_text = " ".join(
        block["text"]
        for block in (message.content or [])
        if isinstance(block, dict) and block.get("type") == "text"
    )

    # Persist rating to Postgres
    message.rating = body.rating
    await db.commit()

    # Upsert to Qdrant feedback_bank (best-effort — never fail the request)
    try:
        vec = await embed(response_text)
        await qdrant.upsert(
            collection_name="feedback_bank",
            points=[
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vec,
                    payload={
                        "message_id": str(msg_id),
                        "agent_id": agent_id,
                        "response_text": response_text,
                        "rating": body.rating,
                    },
                )
            ],
        )
    except Exception:
        logger.exception("Failed to write feedback to Qdrant [message_id=%s]", msg_id)
