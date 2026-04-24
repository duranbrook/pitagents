# Sub-project 2: Quote Agent — Implementation Plan
_Created: 2026-04-23_

## Goal

Add a Quote Agent to the pitagents chat interface that lets the shop owner or technician draft, refine, and finalize repair quotes through natural language. The agent looks up part prices, estimates labor, and builds a structured quote attached to an inspection session.

## Prerequisites

- Sub-project 1 (Web Chat UI) complete — ✅
- Stack running: db, redis, backend (8000), web (3000)
- Branch: create `feat/quote-agent` from `feat/web-chat-ui`

## Architecture Overview

```
User → ChatPanel (agent: "quote") → POST /chat/quote/message → stream_quote agent
                                                                 ├── lookup_part_price (AllData / flat mock)
                                                                 ├── estimate_labor (shop.labor_rate × hours)
                                                                 ├── create_quote_item (writes to DB)
                                                                 ├── list_quote_items (reads from DB)
                                                                 └── finalize_quote (sets status=final)
Quote DB: quotes table (id, session_id, status, line_items JSONB, total, created_at)
```

**Key decisions:**
- One `quotes` table, `line_items` stored as JSONB array (avoids a separate join table for MVP)
- `status` enum: `draft | final | sent`
- Line item shape: `{type: "part"|"labor", description, qty, unit_price, total}`
- Pricing: mock AllData lookup (hardcoded catalog for demo); real AllData API is a stub
- Quote attaches to an `InspectionSession` (nullable — can draft standalone)
- Quote finalize updates `reports.estimate_total` if a report exists for the session

## Tasks

### Task 1 — DB Model: `Quote`
**File:** `backend/src/models/quote.py`

New SQLAlchemy model:
```python
class Quote(Base):
    __tablename__ = "quotes"
    id: UUID PK
    session_id: UUID FK(inspection_sessions.id) nullable
    status: Enum("draft", "final", "sent") default="draft"
    line_items: JSONB default=[]
    total: Numeric(10,2) default=0
    created_at: DateTime server_default=now()
    updated_at: DateTime onupdate=now()
```

Add to `src/db/base.py` import list.

### Task 2 — Alembic Migration: `0002_add_quotes.py`
**File:** `backend/alembic/versions/0002_add_quotes.py`

Create `quotes` table. Also add `quote_id` nullable FK column to `reports` table so a report can reference its quote.

### Task 3 — Quote Tools
**File:** `backend/src/agents/tools/quote_tools.py`

Implement these async functions (all take `db: AsyncSession`):

1. `lookup_part_price(part_name: str) -> dict` — mock catalog lookup. Returns `{part: str, unit_price: float, part_number: str}`. Hardcode 10–15 common parts (brake pads, oil filter, air filter, wiper blades, etc.).

2. `estimate_labor(task_name: str, hours: float, db: AsyncSession) -> dict` — fetches `shop.labor_rate` from DB (use shop id `00000000-0000-0000-0000-000000000099` for test). Returns `{task: str, hours: float, rate: float, total: float}`.

3. `create_quote_item(quote_id: str, item_type: str, description: str, qty: float, unit_price: float, db: AsyncSession) -> dict` — appends a line item to `quotes.line_items` and recalculates `total`. Returns updated quote summary.

4. `list_quote_items(quote_id: str, db: AsyncSession) -> dict` — returns all line items and total for a quote.

5. `create_quote(session_id: str | None, db: AsyncSession) -> dict` — creates a new draft quote, returns `{quote_id: str}`.

6. `finalize_quote(quote_id: str, db: AsyncSession) -> dict` — sets status=final, syncs total to `reports.estimate_total` if session has a report. Returns final quote.

Add `QUOTE_TOOL_SCHEMAS` list (Anthropic tool schema format).

### Task 4 — Quote Agent
**File:** `backend/src/agents/quote_agent.py`

```python
from src.agents.base import stream_response
from src.agents.tools.quote_tools import QUOTE_TOOL_SCHEMAS, ...

_PROMPT = (Path(__file__).parent / "prompts" / "quote_agent.txt").read_text()

async def stream_quote(history, user_content, db: AsyncSession) -> AsyncGenerator:
    async def _tool_executor(name, inp):
        # dispatch to quote_tools functions
    async for event in stream_response(...):
        yield event
```

### Task 5 — Quote Agent Prompt
**File:** `backend/src/agents/prompts/quote_agent.txt`

System prompt covering:
- Role: repair quote specialist for PitAgents auto shop
- Workflow: ask for vehicle context / session ID → look up parts → estimate labor → build quote line by line → finalize
- Tone: professional, concise, shop-floor language
- Always show running total after each item added
- Ask confirmation before finalizing

### Task 6 — Quote API Routes
**File:** `backend/src/api/quotes.py`

```
GET  /quotes                         — list all quotes (filter by status)
POST /quotes                         — create a new draft quote
GET  /quotes/{quote_id}              — get quote with line items
PUT  /quotes/{quote_id}/finalize     — finalize the quote
GET  /sessions/{session_id}/quote    — get quote for a session (or 404)
```

Register in `main.py`.

### Task 7 — Wire Quote Agent into Chat
**File:** `backend/src/api/chat.py`

Add `"quote": stream_quote` to `AGENT_STREAMS`. Pass `db` for the quote agent (same pattern as Tom).

### Task 8 — Frontend: QuoteAgentButton + QuotePanel
**Files:** `web/src/components/QuotePanel.tsx`, `web/src/components/AgentList.tsx`

Add "quote" to the agent list in `AgentList.tsx`. Add a `QuotePanel` component that:
- Renders chat messages (reuse `MessageBubble`)
- Shows a live quote sidebar (fetches `GET /quotes` or `GET /sessions/{id}/quote`)
- Updates quote summary after each agent message
- Has a "Finalize Quote" button that calls `PUT /quotes/{id}/finalize`

### Task 9 — Quote Summary Sidebar
**File:** `web/src/components/QuoteSummary.tsx`

Shows current line items in a table:
```
| Description      | Qty | Unit  | Total |
| Brake Pads       | 1   | $89   | $89   |
| Labor: Brake Job | 2h  | $120/h| $240  |
| TOTAL            |     |       | $329  |
```
Renders from polling `GET /quotes/{quote_id}` every 3s while draft status.

### Task 10 — Backend Tests: Quote Tools + Routes
**Files:** `backend/tests/test_quote_tools.py`, `backend/tests/test_quote_api.py`

Unit tests:
- `test_lookup_part_price_returns_known_part`
- `test_estimate_labor_uses_shop_rate`
- `test_create_quote_item_updates_total`
- `test_finalize_quote_sets_status`
- `test_quote_api_create_returns_201`
- `test_quote_api_get_returns_line_items`
- `test_quote_api_finalize_returns_200`

Target: 90%+ coverage on quote module.

## Smoke Test Checklist

1. Start fresh chat with "quote" agent
2. Say: "I need to quote a brake job for a 2019 Honda Civic"
3. Agent should: create quote → look up brake pads → estimate brake labor → list items → show total
4. Say: "Also add an oil change"
5. Agent adds oil filter + oil change labor
6. Say: "Finalize it"
7. Agent sets status=final
8. `GET /quotes` returns the finalized quote
9. Quote total matches sum of line items

## File Checklist

- [ ] `backend/src/models/quote.py`
- [ ] `backend/alembic/versions/0002_add_quotes.py`
- [ ] `backend/src/agents/tools/quote_tools.py`
- [ ] `backend/src/agents/quote_agent.py`
- [ ] `backend/src/agents/prompts/quote_agent.txt`
- [ ] `backend/src/api/quotes.py`
- [ ] `backend/src/api/chat.py` (add quote agent)
- [ ] `web/src/components/QuotePanel.tsx`
- [ ] `web/src/components/QuoteSummary.tsx`
- [ ] `web/src/components/AgentList.tsx` (add quote entry)
- [ ] `backend/tests/test_quote_tools.py`
- [ ] `backend/tests/test_quote_api.py`

## Estimated Effort

~4–6 hours total (10 tasks, 2 agents, 1 DB migration, frontend panel)
