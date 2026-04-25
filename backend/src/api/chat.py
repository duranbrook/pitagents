import json
import logging
import uuid
import re
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.api.deps import get_current_user
from src.db.base import get_db, AsyncSessionLocal
from src.models.chat_message import ChatMessage
from src.agents.assistant import assistant_graph
from src.agents.tom import tom_graph

logger = logging.getLogger(__name__)

_GUARDRAIL_PATTERNS = [
    re.compile(r"\b(medical|doctor|prescription)\b", re.IGNORECASE),
    re.compile(r"\b(legal advice|lawsuit|sue)\b", re.IGNORECASE),
    re.compile(r"\b(stock|crypto|invest)\b", re.IGNORECASE),
    re.compile(r"ignore (previous|all) instructions", re.IGNORECASE),
]


def _check_guardrails(message: str) -> str | None:
    """Returns the matched pattern string if blocked, None if the message is OK."""
    for pattern in _GUARDRAIL_PATTERNS:
        if pattern.search(message):
            return pattern.pattern
    return None

router = APIRouter(prefix="/chat", tags=["chat"])

AGENT_GRAPHS: dict = {
    "assistant": assistant_graph,
    "tom": tom_graph,
}


class MessageRequest(BaseModel):
    message: str
    image_url: str | None = None


def _build_user_content(message: str, image_url: str | None) -> list[dict]:
    content: list[dict] = []
    if image_url:
        if image_url.startswith("data:"):
            header, _, encoded = image_url.partition(",")
            media_type = header.split(":")[1].split(";")[0]
            content.append({"type": "image", "source": {"type": "base64", "media_type": media_type, "data": encoded}})
        else:
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
    user_content: list[dict],
    final_messages: list[dict],
    tool_calls: list[dict],
    db: AsyncSession,
) -> None:
    db.add(ChatMessage(
        user_id=user_id,
        agent_id=agent_id,
        role="user",
        content=user_content,
    ))
    assistant_msg = final_messages[-1]
    db.add(ChatMessage(
        user_id=user_id,
        agent_id=agent_id,
        role="assistant",
        content=assistant_msg["content"],
        tool_calls=tool_calls if tool_calls else None,
    ))
    await db.commit()


@router.get("/{agent_id}/history")
async def get_history(
    agent_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if agent_id not in AGENT_GRAPHS:
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
    if agent_id not in AGENT_GRAPHS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent '{agent_id}' not found")

    blocked = _check_guardrails(body.message)
    if blocked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message blocked by content policy.",
        )

    user_id = uuid.UUID(current_user["sub"])
    history = await _load_history(user_id, agent_id, db)
    user_content = _build_user_content(body.message, body.image_url)

    initial_state = {
        "messages": history + [{"role": "user", "content": user_content}],
        "tool_calls_log": [],
        "stop_reason": "",
        "intent": "",
        "assembled_prompt": "",
    }
    config = {"configurable": {"db": db}}

    async def event_generator():
        tool_calls: list[dict] = []
        final_messages: list[dict] = []

        graph = AGENT_GRAPHS[agent_id]

        try:
            async for event in graph.astream(initial_state, config, stream_mode="custom"):
                payload = {k: v for k, v in event.items() if k != "_messages"}
                yield f"data: {json.dumps(payload)}\n\n"
                if event.get("type") == "done":
                    tool_calls = event.get("tool_calls", [])
                    final_messages = event.get("_messages", [])
                    if final_messages:
                        try:
                            async with AsyncSessionLocal() as save_db:
                                await _save_messages(user_id, agent_id, user_content, final_messages, tool_calls, save_db)
                        except Exception:
                            logger.exception("Failed to persist chat messages [agent=%s user=%s]", agent_id, user_id)
        except Exception as exc:
            import anthropic as _anthropic
            if isinstance(exc, _anthropic.APIStatusError) and exc.status_code == 529:
                yield f"data: {json.dumps({'type': 'error', 'code': 'overloaded', 'message': 'The AI is overloaded right now. Please try again in a moment.'})}\n\n"
            else:
                logger.exception("Agent stream error [agent=%s user=%s]", agent_id, user_id)
                yield f"data: {json.dumps({'type': 'error', 'code': 'server_error', 'message': 'Something went wrong. Please try again.'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
