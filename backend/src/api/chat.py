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
from src.models.shop_agent import ShopAgent
from src.agents.graph_factory import build_react_graph
from src.agents.tool_registry import build_tool_schemas_and_executor

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

# In-process graph cache: agent_id (str) -> compiled graph
# Cleared on agent update/delete via agents.py
_graph_cache: dict[str, object] = {}

_DEFAULT_INTENT_LABELS = ["GENERAL", "LOOKUP", "ACTION", "ANALYTICS"]
_DEFAULT_PROMPT_BLOCKS: dict[str, str] = {}


async def _get_agent_graph(agent_id: str, shop_id: str, db: AsyncSession):
    """Look up agent from DB, build and cache its LangGraph."""
    if agent_id in _graph_cache:
        return _graph_cache[agent_id]

    result = await db.execute(
        select(ShopAgent).where(
            ShopAgent.id == uuid.UUID(agent_id),
            ShopAgent.shop_id == uuid.UUID(shop_id),
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        return None

    tool_schemas, tool_executor = build_tool_schemas_and_executor(agent.tools or [])
    graph = build_react_graph(
        system_prompt=agent.system_prompt,
        tool_schemas=tool_schemas,
        tool_executor=tool_executor if tool_schemas else None,
        intent_labels=_DEFAULT_INTENT_LABELS,
        prompt_blocks=_DEFAULT_PROMPT_BLOCKS,
    )
    _graph_cache[agent_id] = graph
    return graph


class MessageRequest(BaseModel):
    message: str
    image_url: str | None = None   # kept for backward compat
    image_urls: list[str] = []


def _build_user_content(message: str, image_urls: list[str]) -> list[dict]:
    content: list[dict] = []
    for url in image_urls:
        if url.startswith("data:"):
            header, _, encoded = url.partition(",")
            media_type = header.split(":")[1].split(";")[0]
            content.append({"type": "image", "source": {"type": "base64", "media_type": media_type, "data": encoded}})
        else:
            content.append({"type": "image", "source": {"type": "url", "url": url}})
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


def _strip_base64_images(content: list[dict]) -> list[dict]:
    """Replace inline base64 image data with a placeholder before persisting.

    History re-sent to Anthropic on every turn; storing full base64 blobs causes
    the payload to grow unboundedly until the API returns 413.
    """
    result = []
    for block in content:
        if block.get("type") == "image":
            src = block.get("source", {})
            if src.get("type") == "base64":
                result.append({"type": "text", "text": "[image]"})
                continue
        result.append(block)
    return result


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
        content=_strip_base64_images(user_content),
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
    shop_id = current_user.get("shop_id", "")
    graph = await _get_agent_graph(agent_id, shop_id, db)
    if not graph:
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
    shop_id = current_user.get("shop_id", "")
    graph = await _get_agent_graph(agent_id, shop_id, db)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent '{agent_id}' not found")

    blocked = _check_guardrails(body.message)
    if blocked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message blocked by content policy.",
        )

    user_id = uuid.UUID(current_user["sub"])
    history = await _load_history(user_id, agent_id, db)
    # Merge legacy image_url into image_urls for backward compat
    effective_urls = list(body.image_urls)
    if body.image_url and body.image_url not in effective_urls:
        effective_urls.append(body.image_url)
    user_content = _build_user_content(body.message, effective_urls)

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
                yield f"data: {json.dumps({'type': 'error', 'code': 'server_error', 'message': f'{type(exc).__name__}: {exc}'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


class SyncMessageResponse(BaseModel):
    text: str


@router.post("/{agent_id}/message/sync", response_model=SyncMessageResponse)
async def send_message_sync(
    agent_id: str,
    body: MessageRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SyncMessageResponse:
    shop_id = current_user.get("shop_id", "")
    graph = await _get_agent_graph(agent_id, shop_id, db)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent '{agent_id}' not found")

    blocked = _check_guardrails(body.message)
    if blocked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message blocked by content policy.",
        )

    user_id = uuid.UUID(current_user["sub"])
    history = await _load_history(user_id, agent_id, db)
    # Merge legacy image_url into image_urls for backward compat
    effective_urls = list(body.image_urls)
    if body.image_url and body.image_url not in effective_urls:
        effective_urls.append(body.image_url)
    user_content = _build_user_content(body.message, effective_urls)

    initial_state = {
        "messages": history + [{"role": "user", "content": user_content}],
        "tool_calls_log": [],
        "stop_reason": "",
        "intent": "",
        "assembled_prompt": "",
    }
    config = {"configurable": {"db": db}}

    tool_calls: list[dict] = []
    final_messages: list[dict] = []

    try:
        async for event in graph.astream(initial_state, config, stream_mode="custom"):
            if event.get("type") == "done":
                tool_calls = event.get("tool_calls", [])
                final_messages = event.get("_messages", [])
    except Exception as exc:
        import anthropic as _anthropic
        if isinstance(exc, _anthropic.APIStatusError) and exc.status_code == 529:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI is overloaded. Please try again.")
        logger.exception("Agent sync error [agent=%s user=%s]", agent_id, user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{type(exc).__name__}: {exc}",
        )

    if final_messages:
        try:
            await _save_messages(user_id, agent_id, user_content, final_messages, tool_calls, db)
        except Exception:
            logger.exception("Failed to persist chat messages [agent=%s user=%s]", agent_id, user_id)

    response_text = ""
    if final_messages:
        last_content = final_messages[-1].get("content", [])
        if isinstance(last_content, list):
            response_text = " ".join(
                block.get("text", "") for block in last_content if block.get("type") == "text"
            ).strip()
        elif isinstance(last_content, str):
            response_text = last_content

    return SyncMessageResponse(text=response_text)
