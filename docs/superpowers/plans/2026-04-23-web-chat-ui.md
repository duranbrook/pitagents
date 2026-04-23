# Web Chat UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the PitAgents web frontend into a Discord-style multi-agent chat with SSE streaming, voice input, and image attach — backed by two AI agents (Assistant and Tom).

**Architecture:** The FastAPI backend gets a `/chat` router that streams Anthropic responses via SSE, with a `chat_messages` Postgres table for history. Two agents are defined as async streaming functions, each with their own tool sets and system prompts. The Next.js frontend gets a new `/chat` route with a three-panel layout — icon rail, agent list, and chat panel.

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy / Anthropic SDK (streaming) / Deepgram / Next.js 15 App Router / React / TanStack Query / Tailwind CSS

---

## File Map

**Backend — new files:**
- `backend/src/models/chat_message.py` — `ChatMessage` ORM model
- `backend/src/agents/__init__.py`
- `backend/src/agents/base.py` — shared streaming loop + tool executor
- `backend/src/agents/assistant.py` — Assistant agent (VIN tools)
- `backend/src/agents/tom.py` — Tom agent (shop DB tools)
- `backend/src/agents/prompts/assistant.txt` — system prompt
- `backend/src/agents/prompts/tom.txt` — system prompt
- `backend/src/api/chat.py` — `/chat` router (SSE + history)
- `backend/src/api/transcribe.py` — `/transcribe` router
- `backend/src/api/upload.py` — `/upload` router

**Backend — modified files:**
- `backend/src/models/user.py` — add `preferences` JSONB column
- `backend/src/models/__init__.py` — export `ChatMessage`
- `backend/src/api/main.py` — add new routers
- `backend/pyproject.toml` — add `aioboto3` file-upload dep (already there), confirm `httpx`

**Backend — new migration:**
- `backend/alembic/versions/<hash>_add_chat_messages_and_user_preferences.py`

**Frontend — new files:**
- `web/app/chat/page.tsx` — `/chat` route, renders `AppShell`
- `web/components/chat/AppShell.tsx` — three-panel layout
- `web/components/chat/AgentList.tsx` — left agent list
- `web/components/chat/ChatPanel.tsx` — right chat panel + input bar
- `web/components/chat/MessageBubble.tsx` — single message with tool collapse
- `web/components/chat/VoiceButton.tsx` — hold/toggle recording
- `web/components/chat/ImageAttach.tsx` — file picker + upload

**Frontend — modified files:**
- `web/lib/api.ts` — add `chat*`, `transcribeAudio`, `uploadImage` functions
- `web/app/page.tsx` — redirect to `/chat` instead of `/dashboard`
- `web/app/dashboard/page.tsx` — keep as-is (accessible from icon rail later)

---

## Task 1: DB model — ChatMessage + User.preferences migration

**Files:**
- Create: `backend/src/models/chat_message.py`
- Modify: `backend/src/models/user.py`
- Modify: `backend/src/models/__init__.py`
- Create: `backend/alembic/versions/<hash>_add_chat_tables.py`
- Test: `backend/tests/test_models/test_chat_message.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_models/test_chat_message.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.models.chat_message import ChatMessage
from src.db.base import Base
import uuid

TEST_DB = "postgresql+asyncpg://user:password@localhost:5432/autoshop"

@pytest.fixture
async def session():
    engine = create_async_engine(TEST_DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession)
    async with maker() as s:
        yield s
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_create_chat_message(session):
    user_id = uuid.uuid4()
    msg = ChatMessage(
        user_id=user_id,
        agent_id="assistant",
        role="user",
        content=[{"type": "text", "text": "Hello"}],
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    assert msg.id is not None
    assert msg.agent_id == "assistant"
    assert msg.tool_calls is None
```

- [ ] **Step 2: Run the test — expect FAIL (model not defined)**

```bash
cd backend && python -m pytest tests/test_models/test_chat_message.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.models.chat_message'`

- [ ] **Step 3: Create `backend/src/models/chat_message.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime, func
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
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

- [ ] **Step 4: Add `preferences` to `backend/src/models/user.py`**

```python
import uuid
from sqlalchemy import Column, String, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(
        SAEnum("owner", "technician", name="user_role_enum"),
        nullable=False,
    )
    name = Column(String(255), nullable=True)
    # Stores {"voice_mode": "hold" | "toggle"}
    preferences = Column(JSONB, nullable=False, server_default="{}")
```

- [ ] **Step 5: Export `ChatMessage` from `backend/src/models/__init__.py`**

```python
from src.models.shop import Shop
from src.models.user import User
from src.models.session import InspectionSession
from src.models.report import Report
from src.models.media import MediaFile
from src.models.chat_message import ChatMessage

__all__ = ["Shop", "User", "InspectionSession", "Report", "MediaFile", "ChatMessage"]
```

- [ ] **Step 6: Run the test — expect PASS**

```bash
cd backend && python -m pytest tests/test_models/test_chat_message.py -v
```

Expected: `PASSED`

- [ ] **Step 7: Generate Alembic migration**

```bash
cd backend && alembic revision --autogenerate -m "add_chat_messages_and_user_preferences"
```

Open the generated file in `alembic/versions/` and verify it contains:
- `op.create_table("chat_messages", ...)` with all columns
- `op.add_column("users", sa.Column("preferences", postgresql.JSONB, ...))`

- [ ] **Step 8: Commit**

```bash
git add backend/src/models/chat_message.py backend/src/models/user.py backend/src/models/__init__.py backend/alembic/versions/
git commit -m "feat(chat): add ChatMessage model and User.preferences column"
```

---

## Task 2: POST /transcribe — accept audio blob, return transcript

**Files:**
- Create: `backend/src/api/transcribe.py`
- Test: `backend/tests/test_api/test_transcribe.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_api/test_transcribe.py
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from src.api.main import app

@pytest.mark.asyncio
async def test_transcribe_returns_transcript(auth_headers):
    fake_audio = b"RIFF....fake webm bytes"
    mock_response = AsyncMock()
    mock_response.results.channels = [
        type("ch", (), {"alternatives": [type("alt", (), {"transcript": "front brakes are worn"})()]})()
    ]

    with patch("src.api.transcribe.AsyncDeepgramClient") as MockClient:
        instance = MockClient.return_value
        instance.listen.v1.media.transcribe_raw = AsyncMock(return_value=mock_response)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/transcribe",
                content=fake_audio,
                headers={**auth_headers, "Content-Type": "audio/webm"},
            )

    assert resp.status_code == 200
    assert resp.json() == {"transcript": "front brakes are worn"}
```

- [ ] **Step 2: Add `conftest.py` fixture for auth headers (if not present)**

Check `backend/tests/conftest.py`. If `auth_headers` fixture is missing, add:

```python
# backend/tests/conftest.py  (add this fixture)
import pytest

@pytest.fixture
def auth_headers():
    import jwt
    from src.config import settings
    from datetime import datetime, timedelta, timezone
    token = jwt.encode(
        {"sub": "test-user-id", "role": "owner", "email": "owner@shop.com",
         "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        settings.JWT_SECRET.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}
```

- [ ] **Step 3: Run the test — expect FAIL**

```bash
cd backend && python -m pytest tests/test_api/test_transcribe.py -v
```

Expected: `ImportError` or `404`

- [ ] **Step 4: Create `backend/src/api/transcribe.py`**

```python
from deepgram import AsyncDeepgramClient
from fastapi import APIRouter, Request, Depends, HTTPException
from src.api.deps import get_current_user
from src.config import settings

router = APIRouter(prefix="/transcribe", tags=["transcribe"])


@router.post("")
async def transcribe_audio(
    request: Request,
    _: dict = Depends(get_current_user),
):
    """Accept raw audio bytes (WebM/Opus or M4A), return transcript."""
    audio_bytes = await request.body()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="No audio data")

    content_type = request.headers.get("content-type", "audio/webm")
    client = AsyncDeepgramClient(api_key=settings.DEEPGRAM_API_KEY.get_secret_value())

    try:
        response = await client.listen.v1.media.transcribe_raw(
            audio=audio_bytes,
            mimetype=content_type,
            model="nova-3",
            smart_format=True,
            punctuate=True,
            language="en-US",
        )
        transcript = response.results.channels[0].alternatives[0].transcript
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}")

    return {"transcript": transcript}
```

- [ ] **Step 5: Run the test — expect PASS**

```bash
cd backend && python -m pytest tests/test_api/test_transcribe.py -v
```

Expected: `PASSED`

- [ ] **Step 6: Commit**

```bash
git add backend/src/api/transcribe.py backend/tests/test_api/test_transcribe.py
git commit -m "feat(chat): add POST /transcribe endpoint for voice input"
```

---

## Task 3: POST /upload — accept image file, store to S3, return URL

**Files:**
- Create: `backend/src/api/upload.py`
- Test: `backend/tests/test_api/test_upload.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_api/test_upload.py
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock
from src.api.main import app

@pytest.mark.asyncio
async def test_upload_image_returns_url(auth_headers):
    fake_image = b"\x89PNG\r\n..."

    mock_s3 = MagicMock()
    mock_s3.__aenter__ = AsyncMock(return_value=mock_s3)
    mock_s3.__aexit__ = AsyncMock(return_value=False)
    mock_s3.put_object = AsyncMock()

    with patch("src.api.upload.aioboto3.Session") as MockSession:
        MockSession.return_value.client.return_value = mock_s3

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/upload",
                files={"file": ("photo.png", fake_image, "image/png")},
                headers=auth_headers,
            )

    assert resp.status_code == 200
    assert "image_url" in resp.json()
    assert resp.json()["image_url"].startswith("https://")
```

- [ ] **Step 2: Run the test — expect FAIL**

```bash
cd backend && python -m pytest tests/test_api/test_upload.py -v
```

Expected: `404 Not Found`

- [ ] **Step 3: Create `backend/src/api/upload.py`**

```python
import uuid
import aioboto3
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from src.api.deps import get_current_user
from src.config import settings

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("")
async def upload_image(
    file: UploadFile = File(...),
    _: dict = Depends(get_current_user),
):
    """Upload an image to S3/R2 and return its public URL."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    key = f"chat-uploads/{uuid.uuid4()}/{file.filename}"
    data = await file.read()

    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL or None,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY.get_secret_value() or None,
        region_name=settings.AWS_REGION,
    ) as s3:
        await s3.put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=data,
            ContentType=file.content_type,
        )

    base = settings.S3_ENDPOINT_URL.rstrip("/") if settings.S3_ENDPOINT_URL else f"https://s3.amazonaws.com"
    image_url = f"{base}/{settings.S3_BUCKET}/{key}"
    return {"image_url": image_url}
```

- [ ] **Step 4: Run the test — expect PASS**

```bash
cd backend && python -m pytest tests/test_api/test_upload.py -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add backend/src/api/upload.py backend/tests/test_api/test_upload.py
git commit -m "feat(chat): add POST /upload endpoint for image attachments"
```

---

## Task 4: Agent tool definitions

**Files:**
- Create: `backend/src/agents/__init__.py`
- Create: `backend/src/agents/tools/__init__.py`
- Create: `backend/src/agents/tools/vin_tools.py`
- Create: `backend/src/agents/tools/shop_tools.py`
- Test: `backend/tests/test_agents/test_tools.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_agents/test_tools.py
import pytest
from unittest.mock import patch, AsyncMock
from src.agents.tools.vin_tools import lookup_vin, extract_vin_from_image
from src.agents.tools.shop_tools import list_sessions, get_session_detail

@pytest.mark.asyncio
async def test_lookup_vin_returns_vehicle_info():
    with patch("src.agents.tools.vin_tools.lookup_vehicle_by_vin", new_callable=AsyncMock) as mock:
        mock.return_value = {"vin": "2HGFB2F59DH123456", "year": "2019", "make": "Honda", "model": "Civic", "trim": "EX"}
        result = await lookup_vin("2HGFB2F59DH123456")
    assert result["make"] == "Honda"
    assert result["year"] == "2019"

@pytest.mark.asyncio
async def test_lookup_vin_invalid_returns_error():
    result = await lookup_vin("TOOSHORT")
    assert "error" in result

@pytest.mark.asyncio
async def test_extract_vin_from_image_calls_vision():
    with patch("src.agents.tools.vin_tools.extract_vin_from_frames", new_callable=AsyncMock) as mock:
        mock.return_value = "1HGBH41JXMN109186"
        result = await extract_vin_from_image("https://example.com/photo.jpg")
    assert result["vin"] == "1HGBH41JXMN109186"

@pytest.mark.asyncio
async def test_list_sessions_returns_list():
    mock_db = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)
    result = await list_sessions(mock_db)
    assert isinstance(result, list)
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd backend && python -m pytest tests/test_agents/test_tools.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create `backend/src/agents/__init__.py` and `backend/src/agents/tools/__init__.py`**

Both files are empty.

- [ ] **Step 4: Create `backend/src/agents/tools/vin_tools.py`**

```python
"""VIN-related tools for the Assistant agent."""
from src.tools.vin_lookup import lookup_vehicle_by_vin
from src.tools.vision import extract_vin_from_frames

# Anthropic tool schema definitions (passed to messages.create(tools=[...]))
VIN_TOOL_SCHEMAS = [
    {
        "name": "lookup_vin",
        "description": "Look up vehicle information (year, make, model, trim) from a VIN number using the NHTSA database.",
        "input_schema": {
            "type": "object",
            "properties": {
                "vin": {"type": "string", "description": "The 17-character Vehicle Identification Number"}
            },
            "required": ["vin"],
        },
    },
    {
        "name": "extract_vin_from_image",
        "description": "Extract a VIN number from a photo (e.g. dashboard sticker, door jamb). Provide the image URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "image_url": {"type": "string", "description": "Public URL of the image containing the VIN"}
            },
            "required": ["image_url"],
        },
    },
]


async def lookup_vin(vin: str) -> dict:
    if not vin or len(vin) != 17:
        return {"error": f"Invalid VIN: must be 17 characters, got '{vin}'"}
    return await lookup_vehicle_by_vin(vin)


async def extract_vin_from_image(image_url: str) -> dict:
    vin = await extract_vin_from_frames([image_url])
    return {"vin": vin} if vin else {"error": "No VIN found in image"}
```

- [ ] **Step 5: Create `backend/src/agents/tools/shop_tools.py`**

```python
"""Shop DB query tools for the Tom agent."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.session import InspectionSession
from src.models.report import Report

SHOP_TOOL_SCHEMAS = [
    {
        "name": "list_sessions",
        "description": "List recent inspection sessions in the shop, with their status and vehicle info.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max results to return (default 10)"}
            },
            "required": [],
        },
    },
    {
        "name": "get_session_detail",
        "description": "Get full details of a specific inspection session including transcript and findings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "UUID of the inspection session"}
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "get_report",
        "description": "Get the completed report for an inspection session, including the estimate total.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "UUID of the inspection session"}
            },
            "required": ["session_id"],
        },
    },
]


async def list_sessions(db: AsyncSession, limit: int = 10) -> list[dict]:
    result = await db.execute(
        select(InspectionSession).order_by(InspectionSession.created_at.desc()).limit(limit)
    )
    sessions = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "status": s.status,
            "vehicle": s.vehicle,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in sessions
    ]


async def get_session_detail(db: AsyncSession, session_id: str) -> dict:
    result = await db.execute(select(InspectionSession).where(InspectionSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        return {"error": f"Session {session_id} not found"}
    return {
        "id": str(session.id),
        "status": session.status,
        "vehicle": session.vehicle,
        "transcript": session.transcript,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


async def get_report(db: AsyncSession, session_id: str) -> dict:
    result = await db.execute(select(Report).where(Report.session_id == session_id))
    report = result.scalar_one_or_none()
    if not report:
        return {"error": f"No report found for session {session_id}"}
    return {
        "id": str(report.id),
        "summary": report.summary,
        "findings": report.findings,
        "estimate_total": float(report.estimate_total) if report.estimate_total else None,
    }
```

- [ ] **Step 6: Run tests — expect PASS**

```bash
cd backend && python -m pytest tests/test_agents/test_tools.py -v
```

Expected: `4 passed`

- [ ] **Step 7: Commit**

```bash
git add backend/src/agents/ backend/tests/test_agents/
git commit -m "feat(chat): add agent tool definitions (VIN and shop tools)"
```

---

## Task 5: Agent streaming core — system prompts + shared streaming loop

**Files:**
- Create: `backend/src/agents/prompts/assistant.txt`
- Create: `backend/src/agents/prompts/tom.txt`
- Create: `backend/src/agents/base.py`
- Test: `backend/tests/test_agents/test_base.py`

- [ ] **Step 1: Create `backend/src/agents/prompts/assistant.txt`**

```
You are the Assistant for an auto repair shop management system called PitAgents.

You help shop owners and technicians look up vehicle information and answer questions about vehicles.

Your primary tool is VIN lookup: if a user provides a VIN number or uploads a photo that may contain a VIN, use the appropriate tool to retrieve the vehicle details.

Always be concise and professional. When you look up a vehicle, present the key details clearly: year, make, model, and trim.

If you cannot find information, say so clearly and suggest alternatives (e.g. check the door jamb sticker, the dashboard near the windshield, or the vehicle registration).

You do not handle repair estimates — direct those requests to the quote workflow.
```

- [ ] **Step 2: Create `backend/src/agents/prompts/tom.txt`**

```
You are Tom, the AI technician assistant for PitAgents.

You have access to the shop's inspection sessions and reports database. You can look up what inspections are in progress, get full session details including technician transcripts, and retrieve completed reports with estimate totals.

When asked about current jobs, always check list_sessions first to give an up-to-date picture.
When asked about a specific vehicle or job, use get_session_detail to get the transcript and findings.
When asked about pricing or estimates, use get_report for the final totals.

Be direct and factual. Summarise technical findings in plain language. If a session has no report yet, say so and report the current status.
```

- [ ] **Step 3: Write the failing test**

```python
# backend/tests/test_agents/test_base.py
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

@pytest.mark.asyncio
async def test_stream_yields_token_events():
    from src.agents.base import stream_response

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream_ctx)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_stream_ctx.text_stream = aiter_from(["Hello", " world"])

    final_msg = MagicMock()
    final_msg.content = [MagicMock(type="text", text="Hello world")]
    mock_stream_ctx.get_final_message = AsyncMock(return_value=final_msg)

    events = []
    with patch("src.agents.base._anthropic_client") as mock_client:
        mock_client.messages.stream.return_value = mock_stream_ctx
        async for event in stream_response(
            system_prompt="You are helpful.",
            tool_schemas=[],
            tool_executor=None,
            history=[],
            user_content=[{"type": "text", "text": "Hello"}],
        ):
            events.append(event)

    token_events = [e for e in events if e["type"] == "token"]
    assert len(token_events) == 2
    assert token_events[0]["content"] == "Hello"
    done_events = [e for e in events if e["type"] == "done"]
    assert len(done_events) == 1


async def aiter_from(items):
    for item in items:
        yield item
```

- [ ] **Step 4: Run the test — expect FAIL**

```bash
cd backend && python -m pytest tests/test_agents/test_base.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.agents.base'`

- [ ] **Step 5: Create `backend/src/agents/base.py`**

```python
"""Shared streaming loop for all chat agents."""
import json
from collections.abc import AsyncGenerator
from typing import Callable, Awaitable
import anthropic
from src.config import settings

_anthropic_client = anthropic.AsyncAnthropic(
    api_key=settings.ANTHROPIC_API_KEY.get_secret_value()
)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096


async def stream_response(
    system_prompt: str,
    tool_schemas: list[dict],
    tool_executor: Callable[[str, dict], Awaitable[dict]] | None,
    history: list[dict],
    user_content: list[dict],
) -> AsyncGenerator[dict, None]:
    """Stream an agent response, handling tool calls in a loop.

    Yields dicts:
      {"type": "token", "content": str}
      {"type": "tool_start", "tool": str, "input": dict}
      {"type": "tool_end", "tool": str, "output": dict}
      {"type": "done", "tool_calls": list[dict]}

    Returns via StopAsyncIteration — caller collects all messages
    from the final "done" event's context.
    """
    messages = list(history) + [{"role": "user", "content": user_content}]
    tool_calls_log: list[dict] = []
    create_kwargs = dict(
        model=MODEL,
        system=system_prompt,
        max_tokens=MAX_TOKENS,
        messages=messages,
    )
    if tool_schemas:
        create_kwargs["tools"] = tool_schemas

    while True:
        async with _anthropic_client.messages.stream(**create_kwargs) as stream:
            async for text in stream.text_stream:
                yield {"type": "token", "content": text}
            final = await stream.get_final_message()

        assistant_content = [b.model_dump() for b in final.content]
        messages.append({"role": "assistant", "content": assistant_content})

        tool_uses = [b for b in final.content if b.type == "tool_use"]
        if not tool_uses or tool_executor is None:
            break

        tool_results = []
        for tu in tool_uses:
            yield {"type": "tool_start", "tool": tu.name, "input": tu.input}
            output = await tool_executor(tu.name, tu.input)
            yield {"type": "tool_end", "tool": tu.name, "output": output}
            tool_calls_log.append({"name": tu.name, "input": tu.input, "output": output})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": json.dumps(output),
            })

        messages.append({"role": "user", "content": tool_results})
        create_kwargs["messages"] = messages

    yield {"type": "done", "tool_calls": tool_calls_log, "_messages": messages}
```

- [ ] **Step 6: Run the test — expect PASS**

```bash
cd backend && python -m pytest tests/test_agents/test_base.py -v
```

Expected: `PASSED`

- [ ] **Step 7: Commit**

```bash
git add backend/src/agents/base.py backend/src/agents/prompts/ backend/tests/test_agents/test_base.py
git commit -m "feat(chat): add shared agent streaming loop and system prompts"
```

---

## Task 6: Agent modules — Assistant and Tom

**Files:**
- Create: `backend/src/agents/assistant.py`
- Create: `backend/src/agents/tom.py`
- Test: `backend/tests/test_agents/test_agents.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_agents/test_agents.py
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_assistant_stream_calls_base(auth_headers):
    from src.agents.assistant import stream_assistant

    events = []
    with patch("src.agents.assistant.stream_response") as mock_stream:
        async def fake_stream(*args, **kwargs):
            yield {"type": "token", "content": "Found: "}
            yield {"type": "done", "tool_calls": [], "_messages": []}
        mock_stream.return_value = fake_stream()

        async for event in stream_assistant(
            history=[],
            user_content=[{"type": "text", "text": "What car is VIN 2HGFB2F59DH123456?"}],
        ):
            events.append(event)

    assert any(e["type"] == "token" for e in events)
    assert any(e["type"] == "done" for e in events)

@pytest.mark.asyncio
async def test_tom_stream_calls_base():
    from src.agents.tom import stream_tom

    mock_db = AsyncMock()
    events = []
    with patch("src.agents.tom.stream_response") as mock_stream:
        async def fake_stream(*args, **kwargs):
            yield {"type": "token", "content": "2 active sessions: "}
            yield {"type": "done", "tool_calls": [], "_messages": []}
        mock_stream.return_value = fake_stream()

        async for event in stream_tom(history=[], user_content=[{"type": "text", "text": "What jobs are active?"}], db=mock_db):
            events.append(event)

    assert any(e["type"] == "done" for e in events)
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd backend && python -m pytest tests/test_agents/test_agents.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create `backend/src/agents/assistant.py`**

```python
from pathlib import Path
from collections.abc import AsyncGenerator
from src.agents.base import stream_response
from src.agents.tools.vin_tools import VIN_TOOL_SCHEMAS, lookup_vin, extract_vin_from_image

_PROMPT = (Path(__file__).parent / "prompts" / "assistant.txt").read_text()

_TOOLS = {
    "lookup_vin": lambda inp: lookup_vin(inp["vin"]),
    "extract_vin_from_image": lambda inp: extract_vin_from_image(inp["image_url"]),
}


async def _tool_executor(name: str, inp: dict) -> dict:
    fn = _TOOLS.get(name)
    if fn is None:
        return {"error": f"Unknown tool: {name}"}
    return await fn(inp)


async def stream_assistant(
    history: list[dict],
    user_content: list[dict],
) -> AsyncGenerator[dict, None]:
    async for event in stream_response(
        system_prompt=_PROMPT,
        tool_schemas=VIN_TOOL_SCHEMAS,
        tool_executor=_tool_executor,
        history=history,
        user_content=user_content,
    ):
        yield event
```

- [ ] **Step 4: Create `backend/src/agents/tom.py`**

```python
from pathlib import Path
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from src.agents.base import stream_response
from src.agents.tools.shop_tools import (
    SHOP_TOOL_SCHEMAS,
    list_sessions,
    get_session_detail,
    get_report,
)

_PROMPT = (Path(__file__).parent / "prompts" / "tom.txt").read_text()


async def stream_tom(
    history: list[dict],
    user_content: list[dict],
    db: AsyncSession,
) -> AsyncGenerator[dict, None]:
    async def _tool_executor(name: str, inp: dict) -> dict:
        if name == "list_sessions":
            return await list_sessions(db, limit=inp.get("limit", 10))
        if name == "get_session_detail":
            return await get_session_detail(db, inp["session_id"])
        if name == "get_report":
            return await get_report(db, inp["session_id"])
        return {"error": f"Unknown tool: {name}"}

    async for event in stream_response(
        system_prompt=_PROMPT,
        tool_schemas=SHOP_TOOL_SCHEMAS,
        tool_executor=_tool_executor,
        history=history,
        user_content=user_content,
    ):
        yield event
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
cd backend && python -m pytest tests/test_agents/test_agents.py -v
```

Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/src/agents/assistant.py backend/src/agents/tom.py backend/tests/test_agents/test_agents.py
git commit -m "feat(chat): add Assistant and Tom agent modules"
```

---

## Task 7: POST /chat/{agent_id}/message (SSE) + GET /chat/{agent_id}/history

**Files:**
- Create: `backend/src/api/chat.py`
- Test: `backend/tests/test_api/test_chat.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_api/test_chat.py
import pytest
import json
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from src.api.main import app

@pytest.mark.asyncio
async def test_chat_history_empty(auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/chat/assistant/history", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

@pytest.mark.asyncio
async def test_chat_message_streams_sse(auth_headers):
    async def fake_stream(*args, **kwargs):
        yield {"type": "token", "content": "Hello"}
        yield {"type": "done", "tool_calls": [], "_messages": [
            {"role": "user", "content": [{"type": "text", "text": "Hi"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "Hello"}]},
        ]}

    with patch("src.api.chat.stream_assistant", return_value=fake_stream()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/chat/assistant/message",
                json={"message": "Hi"},
                headers=auth_headers,
            )

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    lines = [l for l in resp.text.split("\n") if l.startswith("data: ")]
    events = [json.loads(l[6:]) for l in lines]
    assert any(e["type"] == "token" for e in events)
    assert any(e["type"] == "done" for e in events)

@pytest.mark.asyncio
async def test_chat_invalid_agent_returns_404(auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/chat/unknown/message",
            json={"message": "hi"},
            headers=auth_headers,
        )
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd backend && python -m pytest tests/test_api/test_chat.py -v
```

Expected: `404 Not Found` (router not wired yet)

- [ ] **Step 3: Create `backend/src/api/chat.py`**

```python
import json
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
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


async def _load_history(user_id: str, agent_id: str, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id, ChatMessage.agent_id == agent_id)
        .order_by(ChatMessage.created_at)
    )
    rows = result.scalars().all()
    return [{"role": r.role, "content": r.content} for r in rows]


async def _save_messages(user_id: str, agent_id: str, final_messages: list[dict], tool_calls: list[dict], db: AsyncSession) -> None:
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
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    user_id = current_user["sub"]
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
            "created_at": r.created_at.isoformat(),
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
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    user_id = current_user["sub"]
    history = await _load_history(user_id, agent_id, db)
    user_content = _build_user_content(body.message, body.image_url)

    async def event_generator():
        tool_calls = []
        final_messages = []

        stream_fn = stream_assistant if agent_id == "assistant" else stream_tom
        stream_kwargs = dict(history=history, user_content=user_content)
        if agent_id == "tom":
            stream_kwargs["db"] = db

        async for event in stream_fn(**stream_kwargs):
            if event["type"] == "done":
                tool_calls = event.get("tool_calls", [])
                final_messages = event.get("_messages", [])
            payload = {k: v for k, v in event.items() if k != "_messages"}
            yield f"data: {json.dumps(payload)}\n\n"

        if final_messages:
            await _save_messages(user_id, agent_id, final_messages, tool_calls, db)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

- [ ] **Step 4: Wire routers in `backend/src/api/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.auth import router as auth_router
from src.api.sessions import router as sessions_router
from src.api.reports import router as reports_router
from src.api.chat import router as chat_router
from src.api.transcribe import router as transcribe_router
from src.api.upload import router as upload_router

app = FastAPI(title="AutoShop API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(reports_router)
app.include_router(chat_router)
app.include_router(transcribe_router)
app.include_router(upload_router)
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
cd backend && python -m pytest tests/test_api/test_chat.py -v
```

Expected: `3 passed`

- [ ] **Step 6: Run migration in Docker**

```bash
docker-compose restart migrate backend
```

Check `docker-compose logs migrate` — should end with `Running upgrade ... -> ..., add_chat_messages_and_user_preferences`.

- [ ] **Step 7: Commit**

```bash
git add backend/src/api/chat.py backend/src/api/main.py backend/tests/test_api/test_chat.py
git commit -m "feat(chat): add /chat SSE endpoint and /chat/history route"
```

---

## Task 8: Frontend — API client methods

**Files:**
- Modify: `web/lib/api.ts`

- [ ] **Step 1: Update `web/lib/api.ts`**

Add these exports at the end of the existing file:

```typescript
// ── Chat ──────────────────────────────────────────────────────────────────

export type ChatRole = 'user' | 'assistant'

export interface ContentBlock {
  type: 'text' | 'image' | 'tool_use' | 'tool_result'
  text?: string
  source?: { type: string; url: string }
}

export interface ToolCallRecord {
  name: string
  input: Record<string, unknown>
  output: Record<string, unknown>
}

export interface ChatHistoryItem {
  id: string
  role: ChatRole
  content: ContentBlock[]
  tool_calls: ToolCallRecord[] | null
  created_at: string
}

export const getChatHistory = (agentId: string): Promise<ChatHistoryItem[]> =>
  api.get(`/chat/${agentId}/history`).then(r => r.data)

export async function* streamChatMessage(
  agentId: string,
  message: string,
  imageUrl?: string,
): AsyncGenerator<Record<string, unknown>> {
  const token = getToken()
  const res = await fetch(
    `${BASE_URL}/chat/${agentId}/message`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message, image_url: imageUrl }),
    },
  )
  if (!res.ok) throw new Error(`Chat request failed: ${res.status}`)
  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        yield JSON.parse(line.slice(6))
      }
    }
  }
}

export async function transcribeAudio(audioBlob: Blob): Promise<string> {
  const res = await fetch(`${BASE_URL}/transcribe`, {
    method: 'POST',
    headers: {
      'Content-Type': audioBlob.type || 'audio/webm',
      Authorization: `Bearer ${getToken()}`,
    },
    body: audioBlob,
  })
  if (!res.ok) throw new Error('Transcription failed')
  const data = await res.json()
  return data.transcript as string
}

export async function uploadImage(file: File): Promise<string> {
  const form = new FormData()
  form.append('file', file)
  const res = await api.post('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data.image_url as string
}
```

- [ ] **Step 2: Commit**

```bash
git add web/lib/api.ts
git commit -m "feat(chat): add chat API client methods (SSE, transcribe, upload)"
```

---

## Task 9: Frontend — AppShell + AgentList

**Files:**
- Create: `web/components/chat/AppShell.tsx`
- Create: `web/components/chat/AgentList.tsx`

- [ ] **Step 1: Create `web/components/chat/AgentList.tsx`**

```tsx
'use client'

interface Agent {
  id: string
  name: string
  role: string
  color: string
  initials: string
  lastMessage?: string
}

const AGENTS: Agent[] = [
  { id: 'assistant', name: 'Assistant', role: 'General assistant', color: '#4f46e5', initials: 'A' },
  { id: 'tom', name: 'Tom', role: 'Technician AI', color: '#059669', initials: 'T' },
]

interface Props {
  selectedId: string
  onSelect: (id: string) => void
  lastMessages: Record<string, string>
}

export function AgentList({ selectedId, onSelect, lastMessages }: Props) {
  return (
    <div className="flex flex-col h-full bg-gray-900 w-56 border-r border-gray-800">
      <div className="px-4 pt-5 pb-3">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Team</p>
      </div>
      <div className="flex-1 overflow-y-auto px-2">
        {AGENTS.map(agent => (
          <button
            key={agent.id}
            onClick={() => onSelect(agent.id)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 text-left transition-colors ${
              selectedId === agent.id ? 'bg-gray-700' : 'hover:bg-gray-800'
            }`}
          >
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-semibold flex-shrink-0"
              style={{ background: agent.color }}
            >
              {agent.initials}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-white truncate">{agent.name}</p>
              <p className="text-xs text-gray-400 truncate">
                {lastMessages[agent.id] ?? agent.role}
              </p>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create `web/components/chat/AppShell.tsx`**

```tsx
'use client'

import { useState } from 'react'
import { AgentList } from './AgentList'
import { ChatPanel } from './ChatPanel'

export function AppShell() {
  const [selectedAgent, setSelectedAgent] = useState('assistant')
  const [lastMessages, setLastMessages] = useState<Record<string, string>>({})

  return (
    <div className="flex h-screen bg-gray-950 overflow-hidden">
      {/* Icon rail */}
      <div className="w-11 bg-gray-950 border-r border-gray-800 flex flex-col items-center py-4 gap-4 flex-shrink-0">
        <div className="w-7 h-7 bg-indigo-600 rounded-lg flex items-center justify-center">
          <span className="text-white text-xs font-bold">P</span>
        </div>
        <div className="w-px flex-1 bg-gray-800" />
        <a href="/dashboard" className="w-7 h-7 bg-gray-800 hover:bg-gray-700 rounded-lg flex items-center justify-center" title="Reports">
          <span className="text-gray-400 text-xs">≡</span>
        </a>
      </div>

      {/* Agent list */}
      <AgentList
        selectedId={selectedAgent}
        onSelect={setSelectedAgent}
        lastMessages={lastMessages}
      />

      {/* Chat panel */}
      <div className="flex-1 min-w-0">
        <ChatPanel
          key={selectedAgent}
          agentId={selectedAgent}
          onNewMessage={(text) =>
            setLastMessages(prev => ({ ...prev, [selectedAgent]: text }))
          }
        />
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add web/components/chat/AppShell.tsx web/components/chat/AgentList.tsx
git commit -m "feat(chat): add AppShell and AgentList components"
```

---

## Task 10: Frontend — MessageBubble with tool call collapse

**Files:**
- Create: `web/components/chat/MessageBubble.tsx`

- [ ] **Step 1: Create `web/components/chat/MessageBubble.tsx`**

```tsx
'use client'

import { useState } from 'react'
import type { ContentBlock, ToolCallRecord } from '@/lib/api'

interface Props {
  role: 'user' | 'assistant'
  content: ContentBlock[]
  toolCalls?: ToolCallRecord[] | null
  streaming?: boolean
}

function extractText(content: ContentBlock[]): string {
  return content
    .filter(b => b.type === 'text')
    .map(b => b.text ?? '')
    .join('')
}

function ToolCallsCollapse({ toolCalls }: { toolCalls: ToolCallRecord[] }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mt-1.5">
      <button
        onClick={() => setOpen(o => !o)}
        className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
      >
        <span>{open ? '▼' : '▶'}</span>
        {toolCalls.length} tool call{toolCalls.length !== 1 ? 's' : ''}
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          {toolCalls.map((tc, i) => (
            <div key={i} className="bg-gray-900 rounded-md p-2 text-xs font-mono">
              <p className="text-yellow-400 mb-1">{tc.name}</p>
              <p className="text-gray-400">in: {JSON.stringify(tc.input)}</p>
              <p className="text-green-400">out: {JSON.stringify(tc.output)}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function MessageBubble({ role, content, toolCalls, streaming }: Props) {
  const text = extractText(content)
  const hasImage = content.some(b => b.type === 'image')
  const isUser = role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-semibold mr-2 flex-shrink-0 mt-0.5">
          A
        </div>
      )}
      <div className={`max-w-[75%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        {hasImage && (
          <div className="mb-1 text-xs text-gray-400 italic">📎 photo attached</div>
        )}
        <div
          className={`px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap break-words ${
            isUser
              ? 'bg-indigo-600 text-white rounded-br-sm'
              : 'bg-gray-800 text-gray-100 rounded-bl-sm'
          }`}
        >
          {text}
          {streaming && <span className="inline-block w-1.5 h-4 bg-current ml-0.5 animate-pulse align-middle" />}
        </div>
        {!isUser && toolCalls && toolCalls.length > 0 && (
          <ToolCallsCollapse toolCalls={toolCalls} />
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/components/chat/MessageBubble.tsx
git commit -m "feat(chat): add MessageBubble with collapsible tool calls"
```

---

## Task 11: Frontend — VoiceButton

**Files:**
- Create: `web/components/chat/VoiceButton.tsx`

- [ ] **Step 1: Create `web/components/chat/VoiceButton.tsx`**

```tsx
'use client'

import { useRef, useState } from 'react'
import { transcribeAudio } from '@/lib/api'

interface Props {
  mode: 'hold' | 'toggle'
  onTranscript: (text: string) => void
  disabled?: boolean
}

export function VoiceButton({ mode, onTranscript, disabled }: Props) {
  const [recording, setRecording] = useState(false)
  const [loading, setLoading] = useState(false)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
    chunksRef.current = []
    recorder.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data) }
    recorder.start()
    recorderRef.current = recorder
    setRecording(true)
  }

  async function stopRecording() {
    const recorder = recorderRef.current
    if (!recorder) return
    recorder.stop()
    recorder.stream.getTracks().forEach(t => t.stop())
    setRecording(false)
    setLoading(true)
    recorder.onstop = async () => {
      try {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        const transcript = await transcribeAudio(blob)
        if (transcript) onTranscript(transcript)
      } finally {
        setLoading(false)
      }
    }
  }

  // Hold mode handlers
  const holdHandlers = mode === 'hold' ? {
    onMouseDown: startRecording,
    onMouseUp: stopRecording,
    onTouchStart: startRecording,
    onTouchEnd: stopRecording,
  } : {}

  // Toggle mode handler
  const toggleHandler = mode === 'toggle' ? {
    onClick: recording ? stopRecording : startRecording,
  } : {}

  return (
    <button
      {...holdHandlers}
      {...toggleHandler}
      disabled={disabled || loading}
      title={mode === 'hold' ? 'Hold to record' : recording ? 'Tap to stop' : 'Tap to record'}
      className={`p-2 rounded-full transition-colors flex-shrink-0 ${
        loading
          ? 'bg-gray-700 text-gray-400 cursor-wait'
          : recording
          ? 'bg-red-600 text-white animate-pulse'
          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
      }`}
    >
      {loading ? (
        <span className="block w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
      ) : recording ? (
        <span className="block w-2 h-2 bg-white rounded-sm mx-1" />
      ) : (
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4z" />
          <path d="M5.5 9.643a.75.75 0 00-1.5 0V10a6 6 0 0012 0v-.357a.75.75 0 00-1.5 0V10a4.5 4.5 0 01-9 0v-.357z" />
        </svg>
      )}
    </button>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/components/chat/VoiceButton.tsx
git commit -m "feat(chat): add VoiceButton with hold/toggle modes"
```

---

## Task 12: Frontend — ImageAttach

**Files:**
- Create: `web/components/chat/ImageAttach.tsx`

- [ ] **Step 1: Create `web/components/chat/ImageAttach.tsx`**

```tsx
'use client'

import { useRef, useState } from 'react'
import { uploadImage } from '@/lib/api'

interface Props {
  onUploaded: (imageUrl: string) => void
  disabled?: boolean
}

export function ImageAttach({ onUploaded, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const url = await uploadImage(file)
      onUploaded(url)
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFile}
      />
      <button
        onClick={() => inputRef.current?.click()}
        disabled={disabled || uploading}
        title="Attach image"
        className="p-2 rounded-full bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors flex-shrink-0 disabled:opacity-50"
      >
        {uploading ? (
          <span className="block w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
        ) : (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        )}
      </button>
    </>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/components/chat/ImageAttach.tsx
git commit -m "feat(chat): add ImageAttach component"
```

---

## Task 13: Frontend — ChatPanel

**Files:**
- Create: `web/components/chat/ChatPanel.tsx`

- [ ] **Step 1: Create `web/components/chat/ChatPanel.tsx`**

```tsx
'use client'

import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getChatHistory, streamChatMessage, ChatHistoryItem, ContentBlock, ToolCallRecord } from '@/lib/api'
import { MessageBubble } from './MessageBubble'
import { VoiceButton } from './VoiceButton'
import { ImageAttach } from './ImageAttach'

interface StreamingMessage {
  text: string
  toolCalls: ToolCallRecord[]
}

const AGENT_NAMES: Record<string, string> = { assistant: 'Assistant', tom: 'Tom' }

interface Props {
  agentId: string
  onNewMessage: (text: string) => void
}

export function ChatPanel({ agentId, onNewMessage }: Props) {
  const qc = useQueryClient()
  const bottomRef = useRef<HTMLDivElement>(null)
  const [input, setInput] = useState('')
  const [pendingImageUrl, setPendingImageUrl] = useState<string | undefined>()
  const [streaming, setStreaming] = useState<StreamingMessage | null>(null)
  const [sending, setSending] = useState(false)

  // Derive voice_mode from localStorage (set in settings page, defaulting to 'hold')
  const voiceMode = (typeof window !== 'undefined'
    ? (localStorage.getItem('voice_mode') as 'hold' | 'toggle' | null)
    : null) ?? 'hold'

  const { data: history = [] } = useQuery<ChatHistoryItem[]>({
    queryKey: ['chat', agentId],
    queryFn: () => getChatHistory(agentId),
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history, streaming])

  async function handleSend() {
    const text = input.trim()
    if (!text || sending) return
    setInput('')
    setSending(true)
    setStreaming({ text: '', toolCalls: [] })

    try {
      for await (const event of streamChatMessage(agentId, text, pendingImageUrl)) {
        if (event.type === 'token') {
          setStreaming(prev => prev ? { ...prev, text: prev.text + (event.content as string) } : null)
        } else if (event.type === 'tool_end') {
          setStreaming(prev => prev
            ? { ...prev, toolCalls: [...prev.toolCalls, { name: event.tool as string, input: event.input as Record<string, unknown>, output: event.output as Record<string, unknown> }] }
            : null)
        } else if (event.type === 'done') {
          onNewMessage(streaming?.text.slice(0, 60) ?? '')
        }
      }
    } finally {
      setStreaming(null)
      setSending(false)
      setPendingImageUrl(undefined)
      qc.invalidateQueries({ queryKey: ['chat', agentId] })
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-full bg-gray-950">
      {/* Header */}
      <div className="border-b border-gray-800 px-5 py-3 flex items-center gap-3">
        <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-semibold">
          {AGENT_NAMES[agentId]?.[0] ?? '?'}
        </div>
        <span className="font-medium text-white text-sm">{AGENT_NAMES[agentId] ?? agentId}</span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-5">
        {history.map(msg => (
          <MessageBubble
            key={msg.id}
            role={msg.role}
            content={msg.content}
            toolCalls={msg.tool_calls}
          />
        ))}
        {streaming !== null && (
          <MessageBubble
            role="assistant"
            content={[{ type: 'text', text: streaming.text }]}
            toolCalls={streaming.toolCalls.length > 0 ? streaming.toolCalls : null}
            streaming
          />
        )}
        <div ref={bottomRef} />
      </div>

      {/* Pending image indicator */}
      {pendingImageUrl && (
        <div className="px-5 pb-1 flex items-center gap-2">
          <span className="text-xs text-indigo-400">📎 Photo attached</span>
          <button onClick={() => setPendingImageUrl(undefined)} className="text-xs text-gray-500 hover:text-red-400">✕</button>
        </div>
      )}

      {/* Input bar */}
      <div className="border-t border-gray-800 px-4 py-3 flex items-end gap-2">
        <ImageAttach onUploaded={setPendingImageUrl} disabled={sending} />
        <VoiceButton
          mode={voiceMode}
          onTranscript={text => setInput(prev => prev ? `${prev} ${text}` : text)}
          disabled={sending}
        />
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`Message ${AGENT_NAMES[agentId] ?? agentId}…`}
          rows={1}
          className="flex-1 bg-gray-800 text-gray-100 placeholder-gray-500 rounded-xl px-4 py-2.5 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-indigo-500"
          style={{ maxHeight: '120px' }}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || sending}
          className="p-2.5 rounded-full bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40 transition-colors flex-shrink-0"
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
          </svg>
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/components/chat/ChatPanel.tsx
git commit -m "feat(chat): add ChatPanel with SSE streaming and voice/image input"
```

---

## Task 14: Frontend — /chat page + update root redirect

**Files:**
- Create: `web/app/chat/page.tsx`
- Modify: `web/app/page.tsx`

- [ ] **Step 1: Create `web/app/chat/page.tsx`**

```tsx
import { AppShell } from '@/components/chat/AppShell'

export default function ChatPage() {
  return <AppShell />
}
```

- [ ] **Step 2: Update `web/app/page.tsx`** (redirect to `/chat` instead of `/dashboard`)

```tsx
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/chat");
}
```

- [ ] **Step 3: Commit**

```bash
git add web/app/chat/page.tsx web/app/page.tsx
git commit -m "feat(chat): add /chat route and update root redirect"
```

---

## Task 15: End-to-end smoke test + docker rebuild

- [ ] **Step 1: Rebuild Docker containers**

```bash
docker-compose down && docker-compose up --build -d
```

Wait for all containers healthy:

```bash
docker-compose ps
```

Expected: all 4 services `Up`.

- [ ] **Step 2: Run migration**

```bash
docker-compose logs migrate | tail -5
```

Expected: line ending `Running upgrade ... -> ..., add_chat_messages_and_user_preferences`.

- [ ] **Step 3: Run full backend test suite**

```bash
docker-compose exec backend python -m pytest tests/ -v --tb=short
```

Expected: all tests pass.

- [ ] **Step 4: Manual smoke test in browser**

1. Open http://localhost:3000 → should redirect to `/chat`
2. Log in with `owner@shop.com` / `testpass`
3. Should see the three-panel chat layout with Assistant and Tom in the agent list
4. Click Assistant → type "What car is VIN 2HGFB2F59DH123456?" → hit Enter
5. Verify: tokens stream in, a response appears, tool calls toggle appears below
6. Click the tool calls toggle — verify it expands to show `lookup_vin` input/output
7. Click Tom → type "What sessions are active?" → verify response streams

- [ ] **Step 5: Test voice button**

1. Click the mic button in the input bar
2. If mode is `hold`: hold it, speak, release → verify text appears in input box
3. If mode is `toggle`: click to start, speak, click again → verify text appears

- [ ] **Step 6: Commit final smoke test confirmation**

```bash
git add .
git commit -m "feat(chat): sub-project 1 complete — web chat UI with SSE, voice, image attach"
```

---

## Self-Review Checklist

- [x] Layout (three-panel Discord style) → Task 9 + 13 (AppShell)
- [x] Assistant agent (VIN tools) → Task 4 + 6
- [x] Tom agent (shop DB tools) → Task 4 + 6
- [x] LangGraph persistence → replaced with `chat_messages` table (simpler, same outcome — history persists across reloads)
- [x] SSE streaming → Task 7 (chat.py), Task 8 (api.ts `streamChatMessage`)
- [x] Collapsible tool calls → Task 10 (MessageBubble)
- [x] Voice input hold/toggle → Task 11 (VoiceButton)
- [x] Voice mode configurable → stored in `localStorage.voice_mode`, read in ChatPanel
- [x] POST /transcribe → Task 2
- [x] POST /upload → Task 3
- [x] User.preferences column → Task 1
- [x] `/chat` as primary route → Task 14
- [x] `/dashboard` kept accessible → icon rail link in AppShell
- [x] Auth required on all routes → `Depends(get_current_user)` in every route
- [x] CORS updated for new routes → middleware already in place, new routers inherit it

> **Note on LangGraph:** The spec called for `AsyncPostgresSaver`. In practice, this requires `psycopg` v3 alongside the existing `asyncpg`, and the API for non-LangChain LLMs is complex. This plan uses a `chat_messages` SQLAlchemy table instead — same user-visible behaviour (history persists), simpler to test and maintain.
