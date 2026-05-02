# Design: Persona Name Voice Agent Switching

**Date:** 2026-05-02  
**Status:** Approved

## Problem

The voice tool requires the client to know the exact agent ID or role name to switch agents. There is no way for a shop owner to give agents human names (e.g. "Tom") and address them naturally by voice ("Tom, are you there?"). The chat header also shows hardcoded names instead of the real active agent.

## Goal

Allow shop owners to assign a human persona name to each agent. When a user addresses that name via voice, the conversation automatically switches to that agent. The chat UI clearly shows who is active at all times.

## Scope

Four changes, in dependency order:

1. Backend data model + API
2. Settings UI
3. Voice session context injection + name matching
4. Chat header fix

---

## Part 1: Data Model

**Change:** Add `persona_name: str | None` to `ShopAgent`.

- Optional field. When set, overrides the role name for voice matching and display.
- Falls back to `name` (role name) when null.
- Added to `AgentResponse`, `AgentCreate`, `AgentUpdate` Pydantic schemas.
- Alembic migration: `ALTER TABLE shop_agents ADD COLUMN persona_name VARCHAR NULL`.
- No backfill needed.

**File:** `backend/src/models/shop_agent.py`  
**Schemas:** `backend/src/api/agents.py`  
**Migration:** new file under `backend/alembic/versions/`

---

## Part 2: Settings UI

**Change:** Add "Persona name" text input to the agent edit form in `/settings` Agents tab.

- Positioned below the agent name field.
- Optional. Placeholder: `e.g. Tom`.
- Wired into the existing `updateAgent` / `createAgent` API calls.
- No new routes, components, or API calls required.

**File:** `web/app/settings/page.tsx` (or the component containing the agent form)

---

## Part 3: Voice Session — Name Context Injection

**Change:** When the voice session initializes, inject a team roster block into the voice system prompt. Update `select_agent` matching to check `persona_name` first.

### System prompt injection

The voice controller fetches the agent list and prepends a block:

```
Your team members are:
- Tom (Service Advisor) — Front desk · Customer intake
- Maria (Technician) — Bay · Inspect & diagnose
- Alex (Parts Manager) — Parts room · Inventory & vendors
...

When the user addresses any team member by name — "Tom, are you there?", "Hey Maria", "Tom could you check this?" — call select_agent with that name immediately, before responding.
```

The block is built from the live agent list at session start. Name changes in settings take effect on the next voice session.

### Name matching update

`select_agent` tool handler checks in order:
1. `agent.persona_name` (case-insensitive)
2. `agent.name` (case-insensitive, existing behavior)

**Files:**  
`web/components/VoiceControlWidget.tsx` — system prompt construction  
`web/lib/voice/tools.ts` or `web/app/chat/page.tsx` — `select_agent` name matching  

---

## Part 4: Chat Header Fix

**Change:** Replace the hardcoded `AGENT_NAMES` dict in `ChatPanel` with the real selected agent object.

### Display

```
[accent color dot]  Tom          ← persona_name if set, else name
                    Bay · Inspect & diagnose  ← role_tagline
```

- Driven by the same `selectedAgent` state used for routing.
- Updates immediately when the voice tool switches agents.
- Removes the hardcoded `AGENT_NAMES` dict entirely.

**File:** `web/components/ChatPanel.tsx`

---

## Data Flow (end to end)

```
Shop owner sets persona_name "Tom" in /settings
        ↓
PATCH /agents/{id} → ShopAgent.persona_name = "Tom" saved in DB
        ↓
User opens voice session
        ↓
VoiceControlWidget fetches agent list → builds roster prompt block
        ↓
User says "Tom, are you there?"
        ↓
Voice LLM sees roster block → calls select_agent("Tom")
        ↓
select_agent matches persona_name "Tom" → switches to Service Advisor agent
        ↓
ChatPanel header updates: "Tom  /  Bay · Inspect & diagnose"
        ↓
Subsequent messages route to /chat/{technician_agent_id}/message
```

---

## Out of Scope

- Creating agents from the voice interface
- Simultaneous multi-agent conversations
- Persistent persona name across browser sessions (already covered by DB)
- TTS/voice personality per agent
