# PitAgents Multi-Agent Chat — Design Spec
**Date:** 2026-04-22  
**Status:** Approved  
**Scope:** Three sequential sub-projects

---

## Overview

Redesign PitAgents from a linear inspection-upload tool into a real-time multi-agent chat platform for auto repair shops. Users interact with AI agents in a messaging interface (Discord/Slack style). The first agent is a general assistant with VIN lookup capability. The second is Tom, an AI that knows everything happening in the shop's inspection pipeline. A technician can speak + photograph a vehicle and receive a structured repair quote back in the same chat thread.

---

## Sub-project 1 — Web Chat UI

### Layout

Three-panel shell, always visible on desktop:

```
┌──────┬───────────────┬─────────────────────────────┐
│ Rail │  Agent List   │        Chat Panel           │
│ 44px │   220px       │       flex: 1               │
└──────┴───────────────┴─────────────────────────────┘
```

- **Icon Rail** (far left, dark background): "Team" icon as the primary section. Expandable to add Reports, Settings, etc. later.
- **Agent List** (middle panel): Each agent shown as avatar + name + last message preview. Active agent highlighted. Clicking switches the chat panel.
- **Chat Panel** (right): Message thread for the selected agent. Input bar at the bottom with text field, image attach button, voice button, and send button.

### Agents

Two agents shipped in this sub-project:

| Agent | Persona | Tools |
|-------|---------|-------|
| **Assistant** | General shop assistant | `extract_vin_from_image`, `lookup_vin` |
| **Tom** | Technician knowledge base | `list_sessions`, `get_session_detail`, `get_report` |

Each agent has its own system prompt defining its persona, scope, and tool descriptions. Prompts live in `backend/src/agents/prompts/`.

### Backend Architecture — LangGraph Chat Graphs

Each agent is a separate LangGraph graph in `backend/src/agents/`:

```
backend/src/agents/
  assistant_graph.py   # VIN + image tools
  tom_graph.py         # DB query tools
  prompts/
    assistant.txt
    tom.txt
  tools/
    vin_tools.py        # extract_vin_from_image, lookup_vin (already in src/tools/)
    shop_tools.py       # list_sessions, get_session_detail, get_report
```

Each graph:
1. `chat_node` — calls Claude (`claude-sonnet-4-6`) with conversation history + tool definitions
2. `tool_node` — LangGraph `ToolNode` executes whichever tool Claude selects
3. Loop: chat_node → tool_node → chat_node until Claude produces a text response with no tool calls

Message history is persisted using `AsyncPostgresSaver` keyed by `thread_id = f"{user_id}:{agent_id}"`. History survives page reloads and sessions.

### API Routes (new)

```
POST /chat/{agent_id}/message
  Body: { message: str, image_url?: str }
  Response: text/event-stream (SSE)
  SSE events:
    { type: "token", content: "..." }
    { type: "tool_start", tool: "lookup_vin", input: {...} }
    { type: "tool_end", tool: "lookup_vin", output: {...} }
    { type: "done" }

GET /chat/{agent_id}/history
  Response: [{ role, content, tool_calls?, created_at }]
```

Auth: Bearer JWT required (same as existing routes).

### Frontend — Chat UI

New route: `/chat` (becomes the primary view after login). `/dashboard` remains accessible via the icon rail as a "Reports" section — it is not removed.

Key components:
- `AppShell` — three-panel layout, manages selected agent state
- `AgentList` — renders agents, previews last message
- `ChatPanel` — message thread + input bar
- `MessageBubble` — renders text with streaming token append; tool calls shown as collapsible "N tool calls ▶" toggle below the final answer
- `VoiceButton` — hold/toggle recording, calls `POST /transcribe` on the FastAPI backend, fills text input on completion
- `ImageAttach` — uploads file to backend, returns `image_url`, appends to message

### Voice Input

Mode is configurable per user in settings. Two modes:

| Mode | Trigger | Behaviour |
|------|---------|-----------|
| `hold` | Hold button | Records while held, transcribes on release, fills input box |
| `toggle` | Tap button | Tap to start, tap again to stop, transcribes, fills input box |

Default: `hold` on web, `toggle` on mobile.

Setting stored in `User.preferences` (JSON column) as `{ voice_mode: "hold" | "toggle" }`.

Transcription flow:
1. Browser `MediaRecorder` captures audio as WebM/Opus
2. On stop, blob is posted to `POST /transcribe` (new FastAPI route wrapping existing `src/tools/transcribe.py`)
3. Backend forwards to Deepgram Nova-3 (already integrated in `src/tools/transcribe.py`)
4. Returns `{ transcript: "..." }` to the frontend
5. Frontend fills the chat input box; user can edit before sending

---

## Sub-project 2 — Technician Quote Agent

### Goal

Technician speaks a description of the problem, optionally takes photos, sends in chat → receives a formatted auto-repair quote as a structured response.

### Trigger

The technician describes the job in chat (by voice or text). The Assistant's system prompt instructs Claude to call `generate_quote` whenever the message describes a repair job (mentions parts, symptoms, or asks for a price). No separate button needed — intent is handled by the prompt.

A `/quote` slash command in the input bar also forces quote mode explicitly, bypassing intent detection.

### Quote Agent Flow

```
Technician message (voice transcript + optional photos)
  → Claude: "Extract findings and generate a repair estimate"
  → tool: extract_findings_from_transcript(transcript)
  → tool: extract_vin_from_image(photo) [if photo provided]
  → tool: lookup_vin(vin) [if VIN extracted]
  → tool: generate_quote(vehicle, findings, labor_rate)
  → Returns: structured Quote JSON
  → Frontend renders quote card in chat
```

### Quote Format

The LLM is given this JSON schema as its output format. The system prompt instructs it to return valid JSON matching this schema:

```json
{
  "estimate_number": "EST-2026-0042",
  "date": "2026-04-22",
  "valid_until": "2026-05-06",
  "shop": { "name": "", "address": "", "phone": "" },
  "customer": { "name": "", "phone": "", "email": "" },
  "vehicle": {
    "year": 2019, "make": "Honda", "model": "Civic", "trim": "EX",
    "vin": "2HGFB2F59DH123456", "mileage": 45000
  },
  "diagnostic_summary": "Technician reports squeaking noise from front left wheel under braking. Photos show brake dust buildup consistent with worn pads.",
  "findings": [
    {
      "description": "Front brake pads worn below minimum thickness",
      "severity": "critical",
      "notes": "Audible squeak, recommend immediate replacement"
    }
  ],
  "parts": [
    {
      "description": "Front brake pad set (OEM equivalent)",
      "part_number": null,
      "quantity": 1,
      "unit_price": 65.00,
      "total": 65.00
    }
  ],
  "labor": [
    {
      "description": "Front brake pad replacement",
      "hours": 1.5,
      "rate": 120.00,
      "total": 180.00
    }
  ],
  "shop_fees": [
    { "description": "Diagnostic fee", "amount": 50.00 },
    { "description": "Shop supplies", "amount": 15.00 },
    { "description": "Environmental disposal", "amount": 10.00 }
  ],
  "subtotal": 320.00,
  "tax_rate": 0.08,
  "tax": 25.60,
  "total": 345.60,
  "terms": "This estimate is valid for 14 days. Final charges may vary if additional issues are discovered during repair. All parts carry a 12-month/12,000-mile warranty."
}
```

`part_number` is `null` for now (future scope: NHTSA parts DB lookup).

### System Prompt Template

Lives in `backend/src/agents/prompts/quote_generation.txt`. The prompt:
- Instructs the LLM to act as a professional auto repair estimator
- Provides the JSON schema above
- Instructs it to use `critical` / `recommended` / `advisory` severity levels
- Provides default labor rate from `Shop.labor_rate`
- Instructs it to be conservative: list only what was described, flag unknowns

### Frontend — Quote Card

When the assistant responds with a quote, the `MessageBubble` renders it as a structured card (not raw JSON):
- Vehicle header with year/make/model
- Collapsible findings table (severity badges)
- Parts + labor table with totals
- Total with tax
- "Save as Report" button → calls existing `POST /reports` to persist it
- "Send to Customer" button → existing send flow

---

## Sub-project 3 — Mobile Chat Interface (iOS + Android)

### Goal

Both existing mobile apps (currently inspection recorders) are redesigned as agent chat clients. Same backend — no new API routes.

### Layout

Mobile adapts the three-panel layout:
- **Sidebar** slides in from left (hamburger or swipe gesture)
- Agent list full-screen when open
- Chat panel full-screen when agent selected
- Input bar: text field + voice button + camera button + send

### Voice Input

Default mode: `toggle` (tap to start, tap to stop). Held-down mode is harder to use on mobile for longer descriptions.

`MediaRecorder` equivalent per platform:
- **Android**: `AudioRecord` API (already used in `CameraX` recording flow), encode as WebM/Opus, `POST /transcribe`
- **iOS**: `AVAudioRecorder`, encode as M4A → convert or send as-is (Deepgram supports M4A), `POST /transcribe`

### Camera

- Technician taps camera button → native camera picker (photo or video)
- Photo: uploaded to `POST /upload` (new lightweight endpoint — just stores to S3, returns `s3_url`; does not create a session)
- `s3_url` attached to next chat message as `image_url`

### Shared Backend

Mobile uses the same `POST /chat/{agent_id}/message` SSE endpoint. SSE is consumed natively:
- **Android**: `OkHttp` SSE listener
- **iOS**: `URLSession` with `dataTask` streaming

---

## Data Model Changes

### New: `User.preferences` column
```sql
ALTER TABLE users ADD COLUMN preferences JSONB DEFAULT '{}';
```
Stores `{ "voice_mode": "hold" | "toggle" }` and future user settings.

### New: LangGraph Postgres checkpointer tables
LangGraph's `AsyncPostgresSaver` creates its own tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_migrations`) via `await checkpointer.setup()` called at app startup.

No custom message table needed — history is stored in LangGraph's checkpoint format.

---

## Future Scope

The following are explicitly out of scope for these three sub-projects. Document in README:

1. **Mechanical sound analysis** — Recording ambient sounds (squeaks, knocks) for AI diagnosis. Requires audio-to-spectrogram pipeline + specialized model or Claude multimodal audio support when available.

2. **Part number lookup** — Resolving part descriptions to OEM/aftermarket part numbers. Requires integration with NHTSA parts catalog, Mitchell1, or shop-specific supplier APIs.

3. **Human technician ↔ owner messaging** — Real-time chat between the shop owner and a human technician via the same interface. Requires WebSocket layer (e.g., Socket.io or FastAPI WebSocket) and a `messages` table.

4. **Multi-shop / team management** — Multiple technicians per shop, role-based agent access, shop-level conversation history.

---

## Implementation Order

1. Sub-project 1 (Web Chat UI) — establishes the foundation all other work builds on
2. Sub-project 2 (Quote Agent) — core value prop, builds on Sub-project 1's agent infrastructure
3. Sub-project 3 (Mobile) — client skin, depends on Sub-projects 1 + 2 backend being stable
