# iOS Technician Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Inspect tab with a role-aware technician chat: VIN-photo vehicle identification, multi-photo/video/voice media input, expandable input area, and a report-card bubble when a quote is finalized.

**Architecture:** Minimal surgical changes to existing files. Backend adds `vehicle_id` to quotes, a DB-lookup VIN tool, multi-image message support, and a video upload endpoint. iOS adds role-based tab routing and a new `TechnicianInputBar` component that plugs into the existing `AgentChatView`.

**Tech Stack:** Python/FastAPI/SQLAlchemy (backend) · Swift/SwiftUI/AVFoundation (iOS) · Alembic (migrations) · pytest-asyncio (backend tests)

---

## File Map

**Backend — create:**
- `backend/alembic/versions/0024_add_vehicle_id_to_quotes.py`
- `backend/tests/test_api/test_upload_video.py`
- `backend/tests/test_tools/test_vin_db_tool.py`
- `backend/tests/test_tools/test_quote_vehicle.py`

**Backend — modify:**
- `backend/src/models/quote.py` — add `vehicle_id` column
- `backend/src/agents/tools/vin_tools.py` — add `find_vehicle_by_vin` tool + schema
- `backend/src/agents/tools/quote_tools.py` — update `create_quote` signature + schema
- `backend/src/agents/tool_registry.py` — wire `find_vehicle_by_vin` into `_exec_vin` + bundle
- `backend/src/api/chat.py` — `image_url: str | None` → `image_urls: list[str]`
- `backend/src/api/upload.py` — add `POST /upload/video`
- `backend/src/api/agents.py` — update Technician system prompt in `DEFAULT_AGENTS`

**iOS — create:**
- `ios/AutoShop/Views/Chat/TechnicianInputBar.swift`
- `ios/AutoShop/Views/Chat/PhotoTrayView.swift`
- `ios/AutoShop/Views/Chat/VINScannerView.swift`
- `ios/AutoShop/Views/Chat/ReportCardBubble.swift`

**iOS — modify:**
- `ios/AutoShop/Network/APIModels.swift` — add `AgentListResponse`, update `ChatRequest`, add `VideoUploadResponse`
- `ios/AutoShop/Network/APIClient.swift` — add `listAgents()`, `uploadVideo()`, `fetchQuote()`
- `ios/AutoShop/AppState.swift` — store `techAgentId`, load on login
- `ios/AutoShop/Views/Main/MainTabView.swift` — role-based tab routing
- `ios/AutoShop/Views/Assistant/AssistantView.swift` — add `showMediaControls`, collapse button, expandable input, report card rendering

---

## PART A — BACKEND

---

### Task 1: Add `vehicle_id` to Quote model + migration

**Files:**
- Modify: `backend/src/models/quote.py`
- Create: `backend/alembic/versions/0024_add_vehicle_id_to_quotes.py`

- [ ] **Step 1: Add column to Quote model**

In `backend/src/models/quote.py`, add after the existing `session_id` column:

```python
vehicle_id = Column(
    UUID(as_uuid=True),
    ForeignKey("vehicles.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
)
```

Full updated model (`quote.py` imports already include `ForeignKey` and `UUID`):
```python
import uuid
from sqlalchemy import Column, String, ForeignKey, Numeric, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("inspection_sessions.id"), nullable=True)
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(String(20), nullable=False, default="draft", server_default="draft")
    line_items = Column(JSON, nullable=False, default=list)
    total = Column(Numeric(10, 2), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

> **Note:** Read the actual `backend/src/models/quote.py` before editing — the columns above may differ. Add only `vehicle_id`; do not change anything else.

- [ ] **Step 2: Write Alembic migration**

Create `backend/alembic/versions/0024_add_vehicle_id_to_quotes.py`:

```python
"""add vehicle_id to quotes

Revision ID: 0024
Revises: 9c5e490936db
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0024"
down_revision = "9c5e490936db"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "quotes",
        sa.Column(
            "vehicle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicles.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_quotes_vehicle_id", "quotes", ["vehicle_id"])


def downgrade() -> None:
    op.drop_index("ix_quotes_vehicle_id", table_name="quotes")
    op.drop_column("quotes", "vehicle_id")
```

> **Note:** Set `down_revision` to the `revision` of the most recent migration in `backend/alembic/versions/`. Check the file listing — it's likely `9c5e490936db`.

- [ ] **Step 3: Run migration**

```bash
cd backend
alembic upgrade head
```

Expected: `Running upgrade ... -> 0024, add vehicle_id to quotes`

- [ ] **Step 4: Commit**

```bash
git add backend/src/models/quote.py backend/alembic/versions/0024_add_vehicle_id_to_quotes.py
git commit -m "feat(db): add vehicle_id FK to quotes table"
```

---

### Task 2: Add `find_vehicle_by_vin` DB-lookup tool

**Files:**
- Modify: `backend/src/agents/tools/vin_tools.py`
- Modify: `backend/src/agents/tool_registry.py`
- Create: `backend/tests/test_tools/test_vin_db_tool.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_tools/test_vin_db_tool.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from src.agents.tools.vin_tools import find_vehicle_by_vin


@pytest.mark.asyncio
async def test_find_vehicle_by_vin_returns_vehicle_data():
    mock_db = AsyncMock(spec=AsyncSession)

    vehicle_row = MagicMock()
    vehicle_row.vehicle_id = "aaa-111"
    vehicle_row.customer_id = "ccc-333"
    vehicle_row.year = 2019
    vehicle_row.make = "Honda"
    vehicle_row.model = "Civic"
    vehicle_row.customer_name = "Sarah Chen"

    mock_result = MagicMock()
    mock_result.first.return_value = vehicle_row
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await find_vehicle_by_vin("1HGBH41JXMN109186", mock_db)

    assert result["vehicle_id"] == "aaa-111"
    assert result["customer_name"] == "Sarah Chen"
    assert result["make"] == "Honda"


@pytest.mark.asyncio
async def test_find_vehicle_by_vin_not_found():
    mock_db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await find_vehicle_by_vin("00000000000000000", mock_db)
    assert "error" in result


@pytest.mark.asyncio
async def test_find_vehicle_by_vin_invalid_vin():
    mock_db = AsyncMock(spec=AsyncSession)
    result = await find_vehicle_by_vin("TOOSHORT", mock_db)
    assert "error" in result
    mock_db.execute.assert_not_called()
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd backend
python -m pytest tests/test_tools/test_vin_db_tool.py -v
```

Expected: `ImportError` or `AttributeError` — `find_vehicle_by_vin` does not exist yet.

- [ ] **Step 3: Add `find_vehicle_by_vin` to `vin_tools.py`**

Append to `backend/src/agents/tools/vin_tools.py`:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.models.vehicle import Vehicle
from src.models.customer import Customer


# Add to VIN_TOOL_SCHEMAS list:
VIN_TOOL_SCHEMAS.append({
    "name": "find_vehicle_by_vin",
    "description": (
        "Look up a vehicle in this shop's database by VIN. "
        "Returns the vehicle_id, customer_id, customer name, year, make, and model. "
        "Use this after reading a VIN from a photo to identify the customer and vehicle."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "vin": {
                "type": "string",
                "description": "The 17-character VIN read from the photo",
            }
        },
        "required": ["vin"],
    },
})


async def find_vehicle_by_vin(vin: str, db: AsyncSession) -> dict:
    vin = vin.upper().strip() if vin else vin
    if not vin or len(vin) != 17:
        return {"error": f"Invalid VIN: must be 17 characters, got '{vin}'"}

    stmt = (
        select(
            Vehicle.id.label("vehicle_id"),
            Vehicle.customer_id,
            Vehicle.year,
            Vehicle.make,
            Vehicle.model,
            Vehicle.trim,
            Customer.name.label("customer_name"),
        )
        .join(Customer, Vehicle.customer_id == Customer.id)
        .where(func.upper(Vehicle.vin) == vin)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        return {"error": f"No vehicle with VIN {vin} found in this shop's records"}

    return {
        "vehicle_id": str(row.vehicle_id),
        "customer_id": str(row.customer_id),
        "customer_name": row.customer_name,
        "year": row.year,
        "make": row.make,
        "model": row.model,
        "trim": row.trim,
    }
```

> **Important:** Add `VIN_TOOL_SCHEMAS.append(...)` AFTER the existing `VIN_TOOL_SCHEMAS = [...]` list definition, not inside it.

- [ ] **Step 4: Wire into tool_registry**

In `backend/src/agents/tool_registry.py`, update the import and executor:

```python
# Update import line:
from src.agents.tools.vin_tools import VIN_TOOL_SCHEMAS, lookup_vin, extract_vin_from_image, find_vehicle_by_vin

# Update _exec_vin to handle the new tool:
async def _exec_vin(name: str, inp: dict, db: AsyncSession) -> dict:
    if name == "lookup_vin":
        return await lookup_vin(inp["vin"])
    if name == "extract_vin_from_image":
        return await extract_vin_from_image(inp["image_url"])
    if name == "find_vehicle_by_vin":
        return await find_vehicle_by_vin(inp["vin"], db)
    return {"error": f"Unknown tool: {name}"}

# Update vin_lookup bundle tool_names set:
"vin_lookup": {
    "label": "VIN Lookup",
    "description": "Identify any vehicle by VIN number or image",
    "schemas": VIN_TOOL_SCHEMAS,
    "executor": _exec_vin,
    "tool_names": {"lookup_vin", "extract_vin_from_image", "find_vehicle_by_vin"},
},
```

- [ ] **Step 5: Run tests**

```bash
cd backend
python -m pytest tests/test_tools/test_vin_db_tool.py -v
```

Expected: all 3 tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/agents/tools/vin_tools.py backend/src/agents/tool_registry.py backend/tests/test_tools/test_vin_db_tool.py
git commit -m "feat(agents): add find_vehicle_by_vin DB-lookup tool"
```

---

### Task 3: Update `create_quote` to accept `vehicle_id`

**Files:**
- Modify: `backend/src/agents/tools/quote_tools.py`
- Modify: `backend/src/agents/tool_registry.py`
- Create: `backend/tests/test_tools/test_quote_vehicle.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_tools/test_quote_vehicle.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from src.agents.tools.quote_tools import create_quote
import uuid


@pytest.mark.asyncio
async def test_create_quote_with_vehicle_id():
    mock_db = AsyncMock(spec=AsyncSession)
    vehicle_id = str(uuid.uuid4())

    fake_quote = MagicMock()
    fake_quote.id = uuid.uuid4()
    fake_quote.status = "draft"

    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    with patch("src.agents.tools.quote_tools.Quote") as MockQuote:
        MockQuote.return_value = fake_quote
        result = await create_quote(mock_db, vehicle_id=vehicle_id)

    call_kwargs = MockQuote.call_args.kwargs
    assert str(call_kwargs["vehicle_id"]) == vehicle_id
    assert result["status"] == "draft"


@pytest.mark.asyncio
async def test_create_quote_without_vehicle_id():
    mock_db = AsyncMock(spec=AsyncSession)
    fake_quote = MagicMock()
    fake_quote.id = uuid.uuid4()
    fake_quote.status = "draft"
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    with patch("src.agents.tools.quote_tools.Quote") as MockQuote:
        MockQuote.return_value = fake_quote
        result = await create_quote(mock_db)

    call_kwargs = MockQuote.call_args.kwargs
    assert call_kwargs.get("vehicle_id") is None
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd backend
python -m pytest tests/test_tools/test_quote_vehicle.py::test_create_quote_with_vehicle_id -v
```

Expected: fails — `create_quote` doesn't accept `vehicle_id` yet.

- [ ] **Step 3: Update `create_quote` in `quote_tools.py`**

Replace the existing `create_quote` function and its schema entry:

```python
# In QUOTE_TOOL_SCHEMAS, update the create_quote entry:
{
    "name": "create_quote",
    "description": (
        "Create a new draft quote in the database, optionally linked to a vehicle (via vehicle_id) "
        "or an inspection session (via session_id). Returns the new quote ID."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "vehicle_id": {
                "type": "string",
                "description": "UUID of the vehicle this quote is for (use when you know the vehicle from a VIN lookup)",
            },
            "session_id": {
                "type": "string",
                "description": "Optional UUID of an inspection session to link this quote to",
            },
        },
        "required": [],
    },
},
```

```python
# Replace the create_quote function:
async def create_quote(
    db: AsyncSession,
    session_id: str | None = None,
    vehicle_id: str | None = None,
) -> dict:
    sid = None
    if session_id:
        try:
            sid = uuid.UUID(session_id)
        except ValueError:
            return {"error": f"Invalid session_id: {session_id}"}

    vid = None
    if vehicle_id:
        try:
            vid = uuid.UUID(vehicle_id)
        except ValueError:
            return {"error": f"Invalid vehicle_id: {vehicle_id}"}

    quote = Quote(session_id=sid, vehicle_id=vid)
    db.add(quote)
    await db.commit()
    await db.refresh(quote)
    return {"quote_id": str(quote.id), "status": quote.status}
```

- [ ] **Step 4: Update tool_registry executor**

In `backend/src/agents/tool_registry.py`, update the `create_quote` dispatch in `_exec_quote`:

```python
if name == "create_quote":
    return await create_quote(db, inp.get("session_id"), inp.get("vehicle_id"))
```

- [ ] **Step 5: Run tests**

```bash
cd backend
python -m pytest tests/test_tools/test_quote_vehicle.py -v
```

Expected: both tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/agents/tools/quote_tools.py backend/src/agents/tool_registry.py backend/tests/test_tools/test_quote_vehicle.py
git commit -m "feat(agents): update create_quote to accept vehicle_id"
```

---

### Task 4: Extend `MessageRequest` to support multiple images

**Files:**
- Modify: `backend/src/api/chat.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_api/test_chat.py` (append, don't replace existing tests):

```python
@pytest.mark.asyncio
async def test_message_request_accepts_multiple_image_urls():
    """Verify the sync endpoint accepts image_urls list."""
    from src.api.chat import MessageRequest
    req = MessageRequest(message="hello", image_urls=["data:image/png;base64,abc", "data:image/jpeg;base64,def"])
    assert len(req.image_urls) == 2

def test_build_user_content_multiple_images():
    from src.api.chat import _build_user_content
    content = _build_user_content("describe these", ["data:image/png;base64,abc", "data:image/jpeg;base64,xyz"])
    image_blocks = [b for b in content if b["type"] == "image"]
    assert len(image_blocks) == 2
    text_blocks = [b for b in content if b["type"] == "text"]
    assert text_blocks[0]["text"] == "describe these"
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend
python -m pytest tests/test_api/test_chat.py::test_message_request_accepts_multiple_image_urls tests/test_api/test_chat.py::test_build_user_content_multiple_images -v
```

Expected: `AttributeError` — `image_urls` doesn't exist yet.

- [ ] **Step 3: Update `MessageRequest` and `_build_user_content` in `chat.py`**

```python
class MessageRequest(BaseModel):
    message: str
    image_url: str | None = None   # keep for backward compat
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
```

In both `send_message` and `send_message_sync`, update the call site:

```python
# Build effective image list: merge legacy image_url into image_urls
effective_urls = list(body.image_urls)
if body.image_url and body.image_url not in effective_urls:
    effective_urls.append(body.image_url)
user_content = _build_user_content(body.message, effective_urls)
```

- [ ] **Step 4: Run tests**

```bash
cd backend
python -m pytest tests/test_api/test_chat.py -v
```

Expected: all tests pass including the two new ones.

- [ ] **Step 5: Commit**

```bash
git add backend/src/api/chat.py backend/tests/test_api/test_chat.py
git commit -m "feat(chat): extend MessageRequest to support multiple image_urls"
```

---

### Task 5: Add `POST /upload/video` endpoint

**Files:**
- Modify: `backend/src/api/upload.py`
- Create: `backend/tests/test_api/test_upload_video.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_api/test_upload_video.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from src.api.main import app


@pytest.mark.asyncio
async def test_upload_video_returns_video_url(auth_headers):
    fake_video = b"\x00\x00\x00\x18ftypmp42"  # minimal MP4 header
    with patch("src.api.upload.storage.upload", new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = "https://bucket.s3.amazonaws.com/videos/test.mp4"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/upload/video",
                files={"file": ("clip.mp4", fake_video, "video/mp4")},
                headers=auth_headers,
            )
    assert resp.status_code == 200
    assert resp.json()["video_url"].startswith("https://")


@pytest.mark.asyncio
async def test_upload_video_rejects_non_video(auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/upload/video",
            files={"file": ("image.png", b"\x89PNG\r\n\x1a\n", "image/png")},
            headers=auth_headers,
        )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_upload_video_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/upload/video",
            files={"file": ("clip.mp4", b"\x00\x00", "video/mp4")},
        )
    assert resp.status_code == 401
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend
python -m pytest tests/test_api/test_upload_video.py -v
```

Expected: 404 — route doesn't exist yet.

- [ ] **Step 3: Add video upload endpoint to `upload.py`**

```python
import uuid as _uuid
from src.storage.s3 import StorageService

storage = StorageService()

ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/x-m4v", "video/mpeg"}
MAX_VIDEO_BYTES = 200 * 1024 * 1024  # 200 MB


class VideoUploadResponse(BaseModel):
    video_url: str


@router.post("/video", response_model=VideoUploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    _: dict = Depends(get_current_user),
):
    if not file.content_type or file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported video type. Allowed: {', '.join(sorted(ALLOWED_VIDEO_TYPES))}",
        )
    data = await file.read()
    if len(data) > MAX_VIDEO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Video too large (max 200 MB)",
        )
    key = f"videos/{_uuid.uuid4()}.mp4"
    video_url = await storage.upload(data, key, file.content_type)
    return VideoUploadResponse(video_url=video_url)
```

- [ ] **Step 4: Run tests**

```bash
cd backend
python -m pytest tests/test_api/test_upload_video.py -v
```

Expected: all 3 pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/api/upload.py backend/tests/test_api/test_upload_video.py
git commit -m "feat(upload): add POST /upload/video endpoint"
```

---

### Task 6: Update Technician agent system prompt

**Files:**
- Modify: `backend/src/api/agents.py`

This updates the `DEFAULT_AGENTS` seed used for new shops. For existing shops, run the SQL in Step 3.

- [ ] **Step 1: Update `DEFAULT_AGENTS[1]` system prompt**

In `backend/src/api/agents.py`, replace the `"Technician"` entry's `system_prompt`:

```python
{
    "name": "Technician",
    "role_tagline": "Bay · Inspect & diagnose",
    "accent_color": "#3b82f6",
    "initials": "TK",
    "system_prompt": (
        "You are the Technician at this auto shop, working in the service bay. "
        "Your domain: vehicle inspection, diagnosis, and repair quotes.\n\n"
        "WORKFLOW:\n"
        "1. When the user sends a VIN photo, read the VIN directly from the image, "
        "then call find_vehicle_by_vin(vin) to identify the vehicle and customer in the shop database. "
        "If not found, call lookup_vin(vin) for vehicle specs and ask the user which customer it belongs to.\n"
        "2. Gather issue details from the technician's description, photos, and voice notes.\n"
        "3. Build the quote: create_quote(vehicle_id=...), then create_quote_item(...) for each part and labor task. "
        "Use lookup_part_price and estimate_labor to get accurate figures.\n"
        "4. When done, call finalize_quote(quote_id=...). "
        "End your reply with the marker [QUOTE:{quote_id}] on its own line so the app can render the report card.\n\n"
        "Always confirm the customer and vehicle before creating a quote. "
        "If uncertain about any detail, ask rather than guess."
    ),
    "tools": ["vin_lookup", "quote_builder", "parts_search", "shop_data"],
    "sort_order": 1,
},
```

- [ ] **Step 2: Update existing Technician agents in the DB**

Run this one-time SQL against your database (Railway or local):

```sql
UPDATE shop_agents
SET system_prompt = 'You are the Technician at this auto shop, working in the service bay. Your domain: vehicle inspection, diagnosis, and repair quotes.

WORKFLOW:
1. When the user sends a VIN photo, read the VIN directly from the image, then call find_vehicle_by_vin(vin) to identify the vehicle and customer in the shop database. If not found, call lookup_vin(vin) for vehicle specs and ask the user which customer it belongs to.
2. Gather issue details from the technician''s description, photos, and voice notes.
3. Build the quote: create_quote(vehicle_id=...), then create_quote_item(...) for each part and labor task. Use lookup_part_price and estimate_labor to get accurate figures.
4. When done, call finalize_quote(quote_id=...). End your reply with the marker [QUOTE:{quote_id}] on its own line so the app can render the report card.

Always confirm the customer and vehicle before creating a quote. If uncertain about any detail, ask rather than guess.'
WHERE name = 'Technician';
```

- [ ] **Step 3: Commit**

```bash
git add backend/src/api/agents.py
git commit -m "feat(agents): update Technician system prompt with VIN + quote workflow"
```

---

## PART B — iOS

---

### Task 7: Add `AgentListResponse` model + `listAgents()` + tech agent loading in `AppState`

**Files:**
- Modify: `ios/AutoShop/Network/APIModels.swift`
- Modify: `ios/AutoShop/Network/APIClient.swift`
- Modify: `ios/AutoShop/AppState.swift`

- [ ] **Step 1: Add `AgentListResponse` to `APIModels.swift`**

Append to `ios/AutoShop/Network/APIModels.swift` in the `// MARK: - Chat` section:

```swift
// MARK: - Agents

struct AgentListItem: Decodable, Identifiable {
    let id: String
    let name: String
    let roleTagline: String
    let accentColor: String
    let initials: String
    let tools: [String]
    let sortOrder: Int
    enum CodingKeys: String, CodingKey {
        case id, name, initials, tools
        case roleTagline = "role_tagline"
        case accentColor = "accent_color"
        case sortOrder = "sort_order"
    }
}

// Also update ChatRequest to support imageUrls:
// (replace existing ChatRequest)
struct ChatRequest: Encodable {
    let message: String
    let imageUrls: [String]
    enum CodingKeys: String, CodingKey {
        case message
        case imageUrls = "image_urls"
    }
}

struct VideoUploadResponse: Decodable {
    let videoUrl: String
    enum CodingKeys: String, CodingKey {
        case videoUrl = "video_url"
    }
}
```

- [ ] **Step 2: Add `listAgents()` and `uploadVideo()` to `APIClient.swift`**

Append to the `// MARK: - Chat` section:

```swift
func listAgents() async throws -> [AgentListItem] {
    try await get("/agents")
}

func fetchQuote(id: String) async throws -> QuoteResponse {
    try await get("/quotes/\(id)")
}
```

Add a new multipart helper and `uploadVideo` method:

```swift
func uploadVideo(data: Data, filename: String) async throws -> VideoUploadResponse {
    guard let url = URL(string: baseURL + "/upload/video") else { throw APIError.invalidURL }
    let boundary = UUID().uuidString
    var req = URLRequest(url: url)
    req.httpMethod = "POST"
    req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
    injectAuth(&req)

    var body = Data()
    body.append("--\(boundary)\r\n".data(using: .utf8)!)
    body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
    body.append("Content-Type: video/mp4\r\n\r\n".data(using: .utf8)!)
    body.append(data)
    body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
    req.httpBody = body

    let (respData, response) = try await URLSession.shared.data(for: req)
    try validate(data: respData, response: response)
    return try decode(VideoUploadResponse.self, from: respData)
}
```

- [ ] **Step 3: Load tech agent ID in `AppState.swift`**

Add `techAgentId` property and `loadTechAgent()` method:

```swift
@MainActor
final class AppState: ObservableObject {
    @Published var token: String?
    @Published var userEmail: String = ""
    @Published var userRole: String = ""
    @Published var shopId: String = ""
    @Published var techAgentId: String = ""   // ← add

    // ... existing init, login, logout, decodeToken unchanged ...

    func loadTechAgent() async {
        guard userRole == "technician" else { return }
        guard let agents = try? await APIClient.shared.listAgents() else { return }
        if let tech = agents.first(where: { $0.name == "Technician" }) ?? agents.first {
            await MainActor.run { techAgentId = tech.id }
        }
    }
}
```

- [ ] **Step 4: Build the app**

```bash
cd ios
xcodebuild \
  -project AutoShop.xcodeproj \
  -scheme AutoShop \
  -configuration Debug \
  -destination "platform=iOS Simulator,name=iPhone 16" \
  build 2>&1 | tail -20
```

Expected: `** BUILD SUCCEEDED **`

- [ ] **Step 5: Commit**

```bash
git add ios/AutoShop/Network/APIModels.swift ios/AutoShop/Network/APIClient.swift ios/AutoShop/AppState.swift
git commit -m "feat(ios): add agent list model, uploadVideo, fetchQuote, tech agent loading"
```

---

### Task 8: Role-based `MainTabView`

**Files:**
- Modify: `ios/AutoShop/Views/Main/MainTabView.swift`

- [ ] **Step 1: Update `MainTabView.swift`**

Replace the file with:

```swift
import SwiftUI

struct MainTabView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        if appState.userRole == "technician" {
            technicianTabs
        } else {
            ownerTabs
        }
    }

    private var technicianTabs: some View {
        TabView {
            NavigationStack {
                CustomerListView()
            }
            .tabItem { Label("Customers", systemImage: "person.2.fill") }

            NavigationStack {
                techChatDestination
            }
            .tabItem { Label("Chat", systemImage: "bubble.left.and.bubble.right.fill") }

            NavigationStack {
                ProfileView()
            }
            .tabItem { Label("Profile", systemImage: "person.crop.circle.fill") }
        }
        .task { await appState.loadTechAgent() }
    }

    @ViewBuilder
    private var techChatDestination: some View {
        if appState.techAgentId.isEmpty {
            ProgressView("Loading…")
        } else {
            let techAgent = Agent(
                id: appState.techAgentId,
                displayName: "Tech Assistant",
                subtitle: "Inspection & quotes",
                systemImage: "wrench.and.screwdriver"
            )
            AgentChatView(agent: techAgent, showMediaControls: true)
        }
    }

    private var ownerTabs: some View {
        TabView {
            NavigationStack {
                CustomerListView()
            }
            .tabItem { Label("Customers", systemImage: "person.2.fill") }

            NavigationStack {
                AssistantView()
            }
            .tabItem { Label("Assistant", systemImage: "bubble.left.and.bubble.right.fill") }

            NavigationStack {
                ProfileView()
            }
            .tabItem { Label("Profile", systemImage: "person.crop.circle.fill") }
        }
    }
}
```

- [ ] **Step 2: Build and boot simulator**

```bash
cd ios
xcodebuild \
  -project AutoShop.xcodeproj \
  -scheme AutoShop \
  -configuration Debug \
  -destination "platform=iOS Simulator,name=iPhone 16" \
  build 2>&1 | tail -5

APP_PATH=$(find ~/Library/Developer/Xcode/DerivedData/AutoShop-*/Build/Products/Debug-iphonesimulator -name "AutoShop.app" -maxdepth 1 | head -1)
xcrun simctl boot "iPhone 16" 2>/dev/null || true
xcrun simctl install booted "$APP_PATH"
xcrun simctl launch booted com.autoshop.app
open -a Simulator
```

- [ ] **Step 3: Verify**

Log in with `owner@shop.com / testpass`. Confirm the tab bar shows **Customers · Assistant · Profile** (no Inspect).

- [ ] **Step 4: Commit**

```bash
git add ios/AutoShop/Views/Main/MainTabView.swift
git commit -m "feat(ios): role-based tab routing — technician sees Chat, owner sees Assistant"
```

---

### Task 9: Add `showMediaControls`, collapse button, and expandable input to `AgentChatView`

**Files:**
- Modify: `ios/AutoShop/Views/Assistant/AssistantView.swift`

This task wires the expansion/collapse state and adds the ⌃ button. The actual `TechnicianInputBar` is created in Task 10 — add a placeholder stub here.

- [ ] **Step 1: Add `showMediaControls` parameter and expansion state**

In `AssistantView.swift`, update `AgentChatView`:

```swift
struct AgentChatView: View {
    let agent: Agent
    let showMediaControls: Bool          // ← add
    @StateObject private var vm = AgentChatViewModel()
    @State private var inputText = ""
    @State private var isExpanded = false  // ← add
    @FocusState private var inputFocused: Bool

    init(agent: Agent, showMediaControls: Bool = false) {   // ← add default
        self.agent = agent
        self.showMediaControls = showMediaControls
    }

    var body: some View {
        VStack(spacing: 0) {
            // Chat history — shrinks to peek strip when expanded
            messageList
                .frame(maxHeight: isExpanded ? 120 : .infinity)

            Divider()

            // Input area
            if showMediaControls {
                TechnicianInputBar(
                    agent: agent,
                    vm: vm,
                    isExpanded: $isExpanded
                )
            } else {
                inputBar
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .principal) { agentNavTitle }
            // Collapse button — only when media controls are active and expanded
            if showMediaControls && isExpanded {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        withAnimation(.spring(response: 0.3)) { isExpanded = false }
                    } label: {
                        Image(systemName: "chevron.down.circle.fill")
                            .foregroundStyle(Color.accentColor)
                            .font(.title3)
                    }
                }
            }
        }
        .alert("Error", isPresented: Binding(
            get: { vm.errorMessage != nil },
            set: { if !$0 { vm.errorMessage = nil } }
        )) {
            Button("OK", role: .cancel) { vm.errorMessage = nil }
        } message: { Text(vm.errorMessage ?? "") }
        .task { await vm.load(agentId: agent.id) }
        .onChange(of: vm.isSending) { sending in
            // Auto-collapse when agent finishes replying
            if !sending && isExpanded {
                withAnimation(.spring(response: 0.3)) { isExpanded = false }
            }
        }
    }

    // ... keep existing agentNavTitle, messageList, inputBar, shouldShowAvatar unchanged
}
```

Also add a stub `TechnicianInputBar` at the bottom of the file (will be replaced in Task 10):

```swift
// Stub — replaced in Task 10
struct TechnicianInputBar: View {
    let agent: Agent
    @ObservedObject var vm: AgentChatViewModel
    @Binding var isExpanded: Bool

    var body: some View {
        Text("Media bar coming in Task 10")
            .padding()
    }
}
```

- [ ] **Step 2: Build**

```bash
cd ios
xcodebuild \
  -project AutoShop.xcodeproj -scheme AutoShop -configuration Debug \
  -destination "platform=iOS Simulator,name=iPhone 16" build 2>&1 | tail -5
```

Expected: `** BUILD SUCCEEDED **`

- [ ] **Step 3: Commit**

```bash
git add ios/AutoShop/Views/Assistant/AssistantView.swift
git commit -m "feat(ios): add showMediaControls, expandable input, collapse button to AgentChatView"
```

---

### Task 10: Implement `TechnicianInputBar` (compact + expanded mode)

**Files:**
- Create: `ios/AutoShop/Views/Chat/TechnicianInputBar.swift`
- Modify: `ios/AutoShop/Views/Assistant/AssistantView.swift` (remove stub)

- [ ] **Step 1: Create `TechnicianInputBar.swift`**

Create `ios/AutoShop/Views/Chat/TechnicianInputBar.swift`:

```swift
import SwiftUI

struct TechnicianInputBar: View {
    let agent: Agent
    @ObservedObject var vm: AgentChatViewModel
    @Binding var isExpanded: Bool

    @State private var inputText = ""
    @State private var attachedPhotos: [AttachedPhoto] = []
    @State private var showPhotoSource = false
    @State private var showVINScanner = false
    @State private var showPhotoPicker = false
    @State private var showVideoRecorder = false
    @State private var isRecordingVoice = false
    @State private var isTranscribing = false
    @State private var transcribeHint = false

    var body: some View {
        Group {
            if isExpanded {
                expandedView
            } else {
                compactView
            }
        }
        .background(Color(UIColor.systemBackground))
    }

    // MARK: - Compact

    private var compactView: some View {
        HStack(alignment: .bottom, spacing: 6) {
            cameraMenuButton
            videoButton
            micButton
            compactTextField
            sendButton
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .padding(.bottom, 4)
    }

    private var compactTextField: some View {
        TextField("Message \(agent.displayName)…", text: $inputText, axis: .vertical)
            .lineLimit(1...3)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(Color(.secondarySystemBackground))
            .clipShape(RoundedRectangle(cornerRadius: 20))
            .onChange(of: inputText) { text in
                if !text.isEmpty { withAnimation { isExpanded = true } }
            }
    }

    // MARK: - Expanded

    private var expandedView: some View {
        VStack(spacing: 8) {
            if transcribeHint {
                HStack {
                    Image(systemName: "mic.fill").foregroundStyle(.secondary)
                    Text("Transcribed — edit freely, then send")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Spacer()
                }
                .padding(.horizontal, 14)
                .padding(.top, 8)
            }

            TextEditor(text: $inputText)
                .font(.body)
                .padding(12)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color.accentColor, lineWidth: 1.5)
                        .background(Color(.systemBackground).clipShape(RoundedRectangle(cornerRadius: 16)))
                )
                .padding(.horizontal, 14)

            if !attachedPhotos.isEmpty {
                PhotoTrayView(photos: $attachedPhotos)
                    .padding(.horizontal, 14)
            }

            HStack(spacing: 8) {
                cameraMenuButton
                videoButton
                micButton
                Spacer()
                Button {
                    sendMessage()
                } label: {
                    Text("Send")
                        .fontWeight(.semibold)
                        .padding(.vertical, 10)
                        .padding(.horizontal, 24)
                        .background(canSend ? Color.accentColor : Color(.systemGray4))
                        .foregroundStyle(.white)
                        .clipShape(Capsule())
                }
                .disabled(!canSend)
            }
            .padding(.horizontal, 14)
            .padding(.bottom, 16)
        }
        .padding(.top, 4)
    }

    // MARK: - Buttons

    private var cameraMenuButton: some View {
        Button { showPhotoSource = true } label: {
            Image(systemName: "camera.fill")
                .font(.system(size: 17))
                .frame(width: 36, height: 36)
                .background(Color(.secondarySystemBackground))
                .clipShape(Circle())
        }
        .confirmationDialog("Add Photo", isPresented: $showPhotoSource, titleVisibility: .hidden) {
            Button("Take Photo") { showPhotoPicker = true }
            Button("Scan VIN") { showVINScanner = true }
            Button("Choose from Library") { showPhotoPicker = true }
            Button("Cancel", role: .cancel) {}
        }
        // Photo picker and VIN scanner sheets are presented in Task 12
        .sheet(isPresented: $showVINScanner) {
            VINScannerView { image in
                attachedPhotos.append(AttachedPhoto(image: image, isVIN: true))
                withAnimation { isExpanded = true }
            }
        }
    }

    private var videoButton: some View {
        Button { showVideoRecorder = true } label: {
            Image(systemName: "video.fill")
                .font(.system(size: 17))
                .frame(width: 36, height: 36)
                .background(Color(.secondarySystemBackground))
                .clipShape(Circle())
        }
        // Video sheet added in Task 15
    }

    private var micButton: some View {
        Button { startVoiceRecording() } label: {
            Image(systemName: isRecordingVoice ? "mic.fill" : "mic")
                .font(.system(size: 17))
                .frame(width: 36, height: 36)
                .background(isRecordingVoice ? Color.red : Color(.secondarySystemBackground))
                .foregroundStyle(isRecordingVoice ? .white : .primary)
                .clipShape(Circle())
        }
    }

    private var sendButton: some View {
        Button { sendMessage() } label: {
            Image(systemName: "arrow.up.circle.fill")
                .font(.system(size: 32))
                .foregroundStyle(canSend ? Color.accentColor : Color(.systemGray3))
        }
        .disabled(!canSend)
    }

    // MARK: - Logic

    private var canSend: Bool {
        !vm.isSending && (!inputText.trimmingCharacters(in: .whitespaces).isEmpty || !attachedPhotos.isEmpty)
    }

    private func sendMessage() {
        let text = inputText.trimmingCharacters(in: .whitespaces)
        let imageUrls = attachedPhotos.filter(\.isSelected).compactMap { $0.base64DataUrl }
        inputText = ""
        attachedPhotos = []
        transcribeHint = false
        Task { await vm.sendWithImages(text: text, imageUrls: imageUrls, agentId: agent.id) }
    }

    private func startVoiceRecording() {
        // Implemented in Task 14
    }
}

// MARK: - Supporting model

struct AttachedPhoto: Identifiable {
    let id = UUID()
    let image: UIImage
    var isVIN: Bool = false
    var isSelected: Bool = true

    var base64DataUrl: String? {
        guard let data = image.jpegData(compressionQuality: 0.8) else { return nil }
        return "data:image/jpeg;base64,\(data.base64EncodedString())"
    }
}
```

- [ ] **Step 2: Update `AgentChatViewModel` to support image_urls**

In `AssistantView.swift`, add `sendWithImages` method to `AgentChatViewModel`:

```swift
func sendWithImages(text: String, imageUrls: [String], agentId: String) async {
    let optimistic = ChatHistoryItem(role: "user", content: text.isEmpty ? "[Photos attached]" : text)
    messages.append(optimistic)
    isSending = true
    defer { isSending = false }
    do {
        let req = ChatRequest(message: text.isEmpty ? "See attached photos" : text, imageUrls: imageUrls)
        _ = try await APIClient.shared.sendChatMessage(req, agentId: agentId)
        messages = try await APIClient.shared.chatHistory(agentId: agentId)
    } catch {
        messages.removeLast()
        errorMessage = error.localizedDescription
    }
}
```

Also update the existing `send(text:agentId:)` to use `ChatRequest(message:imageUrls:)`:

```swift
func send(text: String, agentId: String) async {
    let optimistic = ChatHistoryItem(role: "user", content: text)
    messages.append(optimistic)
    isSending = true
    defer { isSending = false }
    do {
        _ = try await APIClient.shared.sendChatMessage(ChatRequest(message: text, imageUrls: []), agentId: agentId)
        messages = try await APIClient.shared.chatHistory(agentId: agentId)
    } catch {
        messages.removeLast()
        errorMessage = error.localizedDescription
    }
}
```

- [ ] **Step 3: Remove stub from `AssistantView.swift`**

Delete the `// Stub — replaced in Task 10` `TechnicianInputBar` struct from `AssistantView.swift`.

- [ ] **Step 4: Build**

```bash
cd ios
xcodebuild \
  -project AutoShop.xcodeproj -scheme AutoShop -configuration Debug \
  -destination "platform=iOS Simulator,name=iPhone 16" build 2>&1 | tail -5
```

Expected: `** BUILD SUCCEEDED **`

- [ ] **Step 5: Commit**

```bash
git add ios/AutoShop/Views/Chat/TechnicianInputBar.swift ios/AutoShop/Views/Assistant/AssistantView.swift
git commit -m "feat(ios): implement TechnicianInputBar with compact/expanded modes"
```

---

### Task 11: Implement `PhotoTrayView` (multi-select with VIN badge)

**Files:**
- Create: `ios/AutoShop/Views/Chat/PhotoTrayView.swift`

- [ ] **Step 1: Create `PhotoTrayView.swift`**

```swift
import SwiftUI

struct PhotoTrayView: View {
    @Binding var photos: [AttachedPhoto]

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(photos.indices, id: \.self) { i in
                    photoThumb(index: i)
                }
                addMoreButton
            }
        }
    }

    private func photoThumb(index: Int) -> some View {
        let photo = photos[index]
        return ZStack(alignment: .bottomTrailing) {
            Image(uiImage: photo.image)
                .resizable()
                .scaledToFill()
                .frame(width: 60, height: 60)
                .clipped()
                .clipShape(RoundedRectangle(cornerRadius: 10))
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .strokeBorder(
                            photo.isVIN ? Color.orange : (photo.isSelected ? Color.accentColor : Color.clear),
                            lineWidth: 2.5
                        )
                )

            if photo.isVIN {
                Text("VIN")
                    .font(.system(size: 9, weight: .black))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 4)
                    .padding(.vertical, 2)
                    .background(Color.orange)
                    .clipShape(RoundedRectangle(cornerRadius: 4))
                    .padding(3)
            } else if photo.isSelected {
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 16))
                    .foregroundStyle(.white, Color.accentColor)
                    .padding(3)
            }
        }
        .onTapGesture { photos[index].isSelected.toggle() }
        .contextMenu {
            Button {
                photos[index].isVIN = true
                // Deselect VIN flag from others
                for j in photos.indices where j != index { photos[j].isVIN = false }
            } label: { Label("Mark as VIN photo", systemImage: "barcode.viewfinder") }

            Button(role: .destructive) {
                photos.remove(at: index)
            } label: { Label("Remove", systemImage: "trash") }
        }
    }

    private var addMoreButton: some View {
        RoundedRectangle(cornerRadius: 10)
            .strokeBorder(Color(.separator), lineWidth: 1.5, antialiased: true)
            .frame(width: 60, height: 60)
            .overlay(Image(systemName: "plus").foregroundStyle(.secondary))
    }
}
```

- [ ] **Step 2: Build**

```bash
cd ios
xcodebuild \
  -project AutoShop.xcodeproj -scheme AutoShop -configuration Debug \
  -destination "platform=iOS Simulator,name=iPhone 16" build 2>&1 | tail -5
```

Expected: `** BUILD SUCCEEDED **`

- [ ] **Step 3: Commit**

```bash
git add ios/AutoShop/Views/Chat/PhotoTrayView.swift
git commit -m "feat(ios): add PhotoTrayView with multi-select and VIN badge"
```

---

### Task 12: VIN scanner — action sheet + camera with viewfinder overlay

**Files:**
- Create: `ios/AutoShop/Views/Chat/VINScannerView.swift`

- [ ] **Step 1: Create `VINScannerView.swift`**

```swift
import SwiftUI
import AVFoundation

struct VINScannerView: View {
    let onCapture: (UIImage) -> Void
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ZStack {
            VINCamera(onCapture: { image in
                onCapture(image)
                dismiss()
            })
            .ignoresSafeArea()

            // Viewfinder overlay
            VStack {
                Spacer()
                Text("Align VIN plate within the frame")
                    .font(.caption)
                    .foregroundStyle(.white)
                    .padding(8)
                    .background(Color.black.opacity(0.55))
                    .clipShape(Capsule())

                RoundedRectangle(cornerRadius: 8)
                    .strokeBorder(.white, lineWidth: 2)
                    .frame(width: 300, height: 60)
                    .overlay(
                        Rectangle()
                            .fill(Color.white.opacity(0.08))
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                    )
                    .padding(.vertical, 16)

                Button("Cancel") { dismiss() }
                    .foregroundStyle(.white)
                    .padding(.bottom, 40)
            }
        }
    }
}

// MARK: - UIKit camera wrapper

struct VINCamera: UIViewControllerRepresentable {
    let onCapture: (UIImage) -> Void

    func makeCoordinator() -> Coordinator { Coordinator(onCapture: onCapture) }

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.cameraCaptureMode = .photo
        picker.delegate = context.coordinator
        picker.showsCameraControls = true
        return picker
    }

    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    class Coordinator: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let onCapture: (UIImage) -> Void
        init(onCapture: @escaping (UIImage) -> Void) { self.onCapture = onCapture }

        func imagePickerController(_ picker: UIImagePickerController,
                                   didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]) {
            if let image = info[.originalImage] as? UIImage {
                onCapture(image)
            }
            picker.dismiss(animated: true)
        }
        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            picker.dismiss(animated: true)
        }
    }
}
```

> **Note:** `NSCameraUsageDescription` must be in `Info.plist` (it likely already is given the existing `RecordingView`). Verify before building.

- [ ] **Step 2: Build**

```bash
cd ios
xcodebuild \
  -project AutoShop.xcodeproj -scheme AutoShop -configuration Debug \
  -destination "platform=iOS Simulator,name=iPhone 16" build 2>&1 | tail -5
```

Expected: `** BUILD SUCCEEDED **`

- [ ] **Step 3: Commit**

```bash
git add ios/AutoShop/Views/Chat/VINScannerView.swift
git commit -m "feat(ios): add VINScannerView with camera viewfinder overlay"
```

---

### Task 13: Voice input — hold mode + auto-detect mode + transcription

**Files:**
- Modify: `ios/AutoShop/Views/Chat/TechnicianInputBar.swift`

Voice mode is stored in `UserDefaults` with key `"voiceMode"` — values `"hold"` or `"auto"`.

- [ ] **Step 1: Add voice recording logic to `TechnicianInputBar.swift`**

Add these state variables to `TechnicianInputBar`:

```swift
@AppStorage("voiceMode") private var voiceMode = "hold"
@State private var audioRecorder: AVAudioRecorder?
@State private var recordingURL: URL?
```

Replace the `startVoiceRecording()` stub:

```swift
private func startVoiceRecording() {
    guard !isRecordingVoice else {
        stopAndTranscribe()
        return
    }
    let url = FileManager.default.temporaryDirectory.appendingPathComponent("voice_\(UUID().uuidString).m4a")
    let settings: [String: Any] = [
        AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
        AVSampleRateKey: 44100,
        AVNumberOfChannelsKey: 1,
        AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue,
    ]
    do {
        try AVAudioSession.sharedInstance().setCategory(.record, mode: .default, options: [])
        try AVAudioSession.sharedInstance().setActive(true)
        audioRecorder = try AVAudioRecorder(url: url, settings: settings)
        audioRecorder?.record()
        recordingURL = url
        isRecordingVoice = true
        withAnimation { isExpanded = true }
    } catch {
        vm.errorMessage = "Microphone unavailable: \(error.localizedDescription)"
    }
}

private func stopAndTranscribe() {
    audioRecorder?.stop()
    audioRecorder = nil
    isRecordingVoice = false
    guard let url = recordingURL else { return }
    isTranscribing = true
    Task {
        defer { isTranscribing = false }
        do {
            let audioData = try Data(contentsOf: url)
            let transcribed = try await TranscribeClient.transcribe(audioData: audioData)
            await MainActor.run {
                inputText = transcribed
                transcribeHint = true
            }
        } catch {
            vm.errorMessage = "Transcription failed: \(error.localizedDescription)"
        }
    }
}
```

Update `micButton` to support hold gesture:

```swift
private var micButton: some View {
    Image(systemName: isTranscribing ? "waveform" : (isRecordingVoice ? "mic.fill" : "mic"))
        .font(.system(size: 17))
        .frame(width: 36, height: 36)
        .background(isRecordingVoice ? Color.red : Color(.secondarySystemBackground))
        .foregroundStyle(isRecordingVoice ? .white : .primary)
        .clipShape(Circle())
        .gesture(
            voiceMode == "hold"
            ? AnyGesture(
                DragGesture(minimumDistance: 0)
                    .onChanged { _ in if !isRecordingVoice { startVoiceRecording() } }
                    .onEnded { _ in if isRecordingVoice { stopAndTranscribe() } }
              )
            : AnyGesture(
                TapGesture()
                    .onEnded { _ in startVoiceRecording() }
              )
        )
}
```

Add `TranscribeClient` to a new file `ios/AutoShop/Network/TranscribeClient.swift`:

```swift
import Foundation

enum TranscribeClient {
    static func transcribe(audioData: Data) async throws -> String {
        guard let url = URL(string: SessionAPI.baseURL + "/transcribe") else {
            throw APIError.invalidURL
        }
        let boundary = UUID().uuidString
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        if let token = KeychainStore.shared.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"voice.m4a\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: audio/m4a\r\n\r\n".data(using: .utf8)!)
        body.append(audioData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        req.httpBody = body

        let (data, response) = try await URLSession.shared.data(for: req)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw APIError.serverError(0, "Transcription failed")
        }
        struct TranscribeResponse: Decodable { let text: String }
        let result = try JSONDecoder().decode(TranscribeResponse.self, from: data)
        return result.text
    }
}
```

- [ ] **Step 2: Build**

```bash
cd ios
xcodebuild \
  -project AutoShop.xcodeproj -scheme AutoShop -configuration Debug \
  -destination "platform=iOS Simulator,name=iPhone 16" build 2>&1 | tail -5
```

Expected: `** BUILD SUCCEEDED **`

> Voice recording cannot be tested in the simulator (no microphone). Verify visually that the mic button renders correctly.

- [ ] **Step 3: Commit**

```bash
git add ios/AutoShop/Views/Chat/TechnicianInputBar.swift ios/AutoShop/Network/TranscribeClient.swift
git commit -m "feat(ios): add voice-to-text with hold and auto-detect modes"
```

---

### Task 14: Video recording + S3 upload

**Files:**
- Modify: `ios/AutoShop/Views/Chat/TechnicianInputBar.swift`

- [ ] **Step 1: Add `VideoRecorderView.swift`**

Create `ios/AutoShop/Views/Chat/VideoRecorderView.swift`:

```swift
import SwiftUI

struct VideoRecorderView: View {
    let onRecord: (URL) -> Void
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VideoCamera(onRecord: { url in
            onRecord(url)
            dismiss()
        })
        .ignoresSafeArea()
        .overlay(alignment: .topLeading) {
            Button("Cancel") { dismiss() }
                .padding()
                .foregroundStyle(.white)
        }
    }
}

struct VideoCamera: UIViewControllerRepresentable {
    let onRecord: (URL) -> Void

    func makeCoordinator() -> Coordinator { Coordinator(onRecord: onRecord) }

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.mediaTypes = ["public.movie"]
        picker.cameraCaptureMode = .video
        picker.videoQuality = .typeMedium
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    class Coordinator: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let onRecord: (URL) -> Void
        init(onRecord: @escaping (URL) -> Void) { self.onRecord = onRecord }

        func imagePickerController(_ picker: UIImagePickerController,
                                   didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]) {
            if let url = info[.mediaURL] as? URL { onRecord(url) }
            picker.dismiss(animated: true)
        }
        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            picker.dismiss(animated: true)
        }
    }
}
```

- [ ] **Step 2: Wire video upload into `TechnicianInputBar`**

In `TechnicianInputBar`, update `videoButton`:

```swift
private var videoButton: some View {
    Button { showVideoRecorder = true } label: {
        Image(systemName: "video.fill")
            .font(.system(size: 17))
            .frame(width: 36, height: 36)
            .background(Color(.secondarySystemBackground))
            .clipShape(Circle())
    }
    .sheet(isPresented: $showVideoRecorder) {
        VideoRecorderView { url in
            Task { await uploadVideo(at: url) }
        }
    }
}

@State private var isUploadingVideo = false

private func uploadVideo(at url: URL) async {
    isUploadingVideo = true
    defer { isUploadingVideo = false }
    do {
        let data = try Data(contentsOf: url)
        let response = try await APIClient.shared.uploadVideo(data: data, filename: url.lastPathComponent)
        await MainActor.run {
            // Append a "video attached" note to the input text
            let note = "[Video attached: \(response.videoUrl)]"
            inputText = inputText.isEmpty ? note : "\(inputText)\n\(note)"
            withAnimation { isExpanded = true }
        }
    } catch {
        vm.errorMessage = "Video upload failed: \(error.localizedDescription)"
    }
}
```

- [ ] **Step 3: Build**

```bash
cd ios
xcodebuild \
  -project AutoShop.xcodeproj -scheme AutoShop -configuration Debug \
  -destination "platform=iOS Simulator,name=iPhone 16" build 2>&1 | tail -5
```

Expected: `** BUILD SUCCEEDED **`

> Video recording cannot be tested in the simulator. Verify the video button renders and the sheet opens.

- [ ] **Step 4: Commit**

```bash
git add ios/AutoShop/Views/Chat/ ios/AutoShop/Views/Assistant/AssistantView.swift
git commit -m "feat(ios): add video recording and S3 upload to TechnicianInputBar"
```

---

### Task 15: `ReportCardBubble` — quote_id detection + card rendering

**Files:**
- Create: `ios/AutoShop/Views/Chat/ReportCardBubble.swift`
- Modify: `ios/AutoShop/Views/Assistant/AssistantView.swift`

The tech agent ends its finalization message with `[QUOTE:{quote_id}]`. The iOS app parses this, fetches the quote, and renders a card below the text bubble.

- [ ] **Step 1: Create `ReportCardBubble.swift`**

```swift
import SwiftUI

struct ReportCardBubble: View {
    let quoteId: String
    @State private var quote: QuoteResponse?
    @State private var isLoading = true

    var body: some View {
        Group {
            if isLoading {
                ProgressView().padding()
            } else if let q = quote {
                card(q)
            }
        }
        .task { await load() }
    }

    private func card(_ q: QuoteResponse) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header
            VStack(alignment: .leading, spacing: 3) {
                Text("INSPECTION REPORT")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(.white.opacity(0.75))
                Text("Quote #\(String(q.quoteId.prefix(8)))")
                    .font(.headline)
                    .foregroundStyle(.white)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(14)
            .background(
                LinearGradient(colors: [Color(hex: "#0060E0"), Color(hex: "#0040A0")],
                               startPoint: .topLeading, endPoint: .bottomTrailing)
            )

            // Line items
            VStack(alignment: .leading, spacing: 4) {
                ForEach(q.lineItems) { item in
                    HStack {
                        Text(item.description)
                            .font(.subheadline)
                            .foregroundStyle(.primary)
                        Spacer()
                        Text(String(format: "$%.2f", item.total))
                            .font(.subheadline.monospacedDigit())
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .padding(14)

            Divider()

            HStack {
                Text("Total")
                    .font(.headline)
                Spacer()
                Text(String(format: "$%.2f", q.total))
                    .font(.headline.monospacedDigit())
            }
            .padding(14)

            Divider()

            Button {
                // Open web report — URL TBD (out of scope for this phase)
            } label: {
                Label("View full report", systemImage: "link")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(Color.accentColor)
                    .frame(maxWidth: .infinity)
                    .padding(12)
            }
        }
        .background(Color(UIColor.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 18))
        .overlay(RoundedRectangle(cornerRadius: 18).strokeBorder(Color(.separator), lineWidth: 0.5))
        .frame(maxWidth: 280)
    }

    private func load() async {
        isLoading = true
        defer { isLoading = false }
        quote = try? await APIClient.shared.fetchQuote(id: quoteId)
    }
}

// Convenience hex color init
extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let r, g, b: Double
        (r, g, b) = (Double((int >> 16) & 0xFF) / 255, Double((int >> 8) & 0xFF) / 255, Double(int & 0xFF) / 255)
        self.init(.sRGB, red: r, green: g, blue: b)
    }
}
```

- [ ] **Step 2: Add quote_id parsing to `ChatHistoryItem`**

In `APIModels.swift`, add an extension:

```swift
extension ChatHistoryItem {
    /// Parses [QUOTE:uuid] marker from the last line of the message.
    var quoteId: String? {
        let text = displayText
        guard let range = text.range(of: #"\[QUOTE:([0-9a-f\-]+)\]"#, options: .regularExpression) else {
            return nil
        }
        let match = String(text[range])
        return match
            .dropFirst("[QUOTE:".count)
            .dropLast(1)
            .isEmpty ? nil : String(match.dropFirst("[QUOTE:".count).dropLast(1))
    }

    /// Display text with the [QUOTE:...] marker stripped.
    var displayTextClean: String {
        displayText
            .replacingOccurrences(of: #"\[QUOTE:[0-9a-f\-]+\]\n?"#, with: "", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
```

- [ ] **Step 3: Render `ReportCardBubble` in `AgentChatView`**

In `AssistantView.swift`, update the `ChatBubble` rendering inside the `LazyVStack` in `messageList`. Replace the `ForEach` body:

```swift
ForEach(Array(vm.messages.enumerated()), id: \.element.id) { idx, msg in
    ChatBubble(item: msg, agent: agent, showAvatar: shouldShowAvatar(at: idx))
        .id(msg.id)
    // Render report card below the agent bubble if it contains a quote
    if msg.role != "user", let qid = msg.quoteId {
        HStack {
            Color.clear.frame(width: 28 + 6)  // avatar width + gap
            ReportCardBubble(quoteId: qid)
            Spacer(minLength: 8)
        }
        .padding(.horizontal, 8)
        .padding(.bottom, 4)
    }
}
```

Update `ChatBubble` to use `displayTextClean` instead of `displayText`:

```swift
Text(item.displayTextClean.isEmpty ? "…" : item.displayTextClean)
```

- [ ] **Step 4: Build**

```bash
cd ios
xcodebuild \
  -project AutoShop.xcodeproj -scheme AutoShop -configuration Debug \
  -destination "platform=iOS Simulator,name=iPhone 16" build 2>&1 | tail -5
```

Expected: `** BUILD SUCCEEDED **`

- [ ] **Step 5: Install and verify**

```bash
APP_PATH=$(find ~/Library/Developer/Xcode/DerivedData/AutoShop-*/Build/Products/Debug-iphonesimulator -name "AutoShop.app" -maxdepth 1 | head -1)
xcrun simctl install booted "$APP_PATH"
xcrun simctl launch booted com.autoshop.app
```

Log in as a technician, navigate to the Chat tab, confirm the tech agent loads and the input bar shows three media buttons.

- [ ] **Step 6: Commit**

```bash
git add ios/AutoShop/Views/Chat/ReportCardBubble.swift ios/AutoShop/Views/Assistant/AssistantView.swift ios/AutoShop/Network/APIModels.swift
git commit -m "feat(ios): add ReportCardBubble with quote_id detection"
```

---

## Self-Review Checklist

After all tasks are complete, verify coverage against the spec:

| Spec requirement | Task(s) |
|---|---|
| Role-based tab routing (technician: Chat/Customers/Profile) | 8 |
| Tech agent loaded from /agents API | 7 |
| Inspect tab removed | 8 |
| TechnicianInputBar (compact + expanded) | 10 |
| Auto-expand on content, manual collapse ⌃ | 9, 10 |
| Camera → action sheet (Take Photo / Scan VIN / Library) | 10 |
| Multi-photo tray with VIN badge + selection | 11, 12 |
| VIN scanner viewfinder overlay | 12 |
| Voice-to-text (hold + auto-detect, configurable) | 13 |
| Transcribed text editable before send | 13 |
| Video recording + audio + S3 upload | 14 |
| Multi-image in chat message | 10 (sendWithImages) |
| `find_vehicle_by_vin` DB-lookup tool | 2 |
| `create_quote(vehicle_id)` | 3 |
| `MessageRequest.image_urls` | 4 |
| `POST /upload/video` | 5 |
| Technician system prompt with VIN + quote workflow | 6 |
| `[QUOTE:id]` detection + ReportCardBubble | 15 |
| Quote migration | 1 |
