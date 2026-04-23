import json
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.api.deps import get_current_user
from src.db.base import get_db
from src.models.chat_message import ChatMessage
from src.agents.assistant import stream_assistant
from src.agents.tom import stream_tom

router = APIRouter(prefix="/chat", tags=["chat"])

AGENTS = {"assistant", "tom"}


class MessageRequest(BaseModel):
    message: str
    image_url: str | None = None


def _build_user_content(message: str, image_url: str | None) -> list[dict]:
    content: list[dict] = []
    if image_url:
        content.append({"type": "image", "source": {"type": "url", "url": image_url}})
    content.append({"type": "text", "text": message})
    return content


async def _load_history(user_id: uuid.UUID, agent_id: str, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id, ChatMessage.agent_id == agent_id)
        .order_by(ChatMessage.created_at)
    )
    rows = result.scalars().all()
    return [{"role": r.role, "content": r.content} for r in rows]


async def _save_messages(
    user_id: uuid.UUID,
    agent_id: str,
    final_messages: list[dict],
    tool_calls: list[dict],
    db: AsyncSession,
) -> None:
    # final_messages is the full thread; save only the new tail (user + assistant)
    for msg in final_messages[-2:]:
        tc = tool_calls if msg["role"] == "assistant" and tool_calls else None
        db.add(ChatMessage(
            user_id=user_id,
            agent_id=agent_id,
            role=msg["role"],
            content=msg["content"],
            tool_calls=tc,
        ))
    await db.commit()


@router.get("/{agent_id}/history")
async def get_history(
    agent_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if agent_id not in AGENTS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent '{agent_id}' not found")
    user_id = uuid.UUID(current_user["sub"])
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id, ChatMessage.agent_id == agent_id)
        .order_by(ChatMessage.created_at)
    )
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "role": r.role,
            "content": r.content,
            "tool_calls": r.tool_calls,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/{agent_id}/message")
async def send_message(
    agent_id: str,
    body: MessageRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if agent_id not in AGENTS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent '{agent_id}' not found")

    user_id = uuid.UUID(current_user["sub"])
    history = await _load_history(user_id, agent_id, db)
    user_content = _build_user_content(body.message, body.image_url)

    async def event_generator():
        tool_calls: list[dict] = []
        final_messages: list[dict] = []

        if agent_id == "assistant":
            stream = stream_assistant(history=history, user_content=user_content)
        else:
            stream = stream_tom(history=history, user_content=user_content, db=db)

        async for event in stream:
            if event["type"] == "done":
                tool_calls = event.get("tool_calls", [])
                final_messages = event.get("_messages", [])
            payload = {k: v for k, v in event.items() if k != "_messages"}
            yield f"data: {json.dumps(payload)}\n\n"

        if final_messages:
            await _save_messages(user_id, agent_id, final_messages, tool_calls, db)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
