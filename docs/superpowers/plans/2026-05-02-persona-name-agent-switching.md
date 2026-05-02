# Persona Name Voice Agent Switching — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let shop owners assign human names (e.g. "Tom") to agents so that saying "Tom, are you there?" via voice automatically switches the active chat agent, with the UI clearly showing who is active.

**Architecture:** Add an optional `persona_name` field to `ShopAgent` (DB + API + frontend types). The voice controller injects a live roster (persona names + role taglines) into the session system prompt so the voice LLM naturally calls `select_agent("Tom")` when it hears a name. The chat page's `registerSelectAgent` callback is updated to match on `persona_name` first. The chat header is fixed to show the real agent name and role tagline instead of a hardcoded dict.

**Tech Stack:** Python/SQLAlchemy (backend model), Alembic (migration), FastAPI/Pydantic (API schemas), TypeScript/React (frontend types + settings form + voice + chat header), TanStack Query (data fetching), OpenAI Realtime API (voice session)

---

## File Map

| File | Change |
|------|--------|
| `backend/alembic/versions/0023_add_persona_name.py` | New migration: add `persona_name VARCHAR NULL` column |
| `backend/src/models/shop_agent.py` | Add `persona_name` SQLAlchemy column |
| `backend/src/api/agents.py` | Add `persona_name` to `AgentResponse`, `AgentCreate`, `AgentUpdate`, `_to_response` |
| `backend/tests/test_api/test_agents.py` | New: tests that `persona_name` round-trips through the API |
| `web/lib/types.ts` | Add `persona_name?: string \| null` to `ShopAgent`, `AgentCreate`, `AgentUpdate` |
| `web/app/settings/page.tsx` | Add persona name input to agent edit form |
| `web/components/VoiceControlWidget.tsx` | Build dynamic instructions with agent roster; include persona names in `agentNames` list |
| `web/app/chat/page.tsx` | Update `registerSelectAgent` to match `persona_name`; pass active `agent` object to `ChatPanel` |
| `web/components/chat/ChatPanel.tsx` | Accept `agent` prop; display persona name + role tagline; remove `AGENT_NAMES` dict |

---

## Task 1: DB Migration

**Files:**
- Create: `backend/alembic/versions/0023_add_persona_name.py`

- [ ] **Step 1: Write the migration file**

```python
# backend/alembic/versions/0023_add_persona_name.py
"""add_persona_name_to_shop_agents

Revision ID: 0023
Revises: 0022
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = '0023'
down_revision = '0022'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('shop_agents', sa.Column('persona_name', sa.String(), nullable=True))


def downgrade():
    op.drop_column('shop_agents', 'persona_name')
```

- [ ] **Step 2: Verify Alembic recognizes it**

```bash
cd backend
alembic heads
```

Expected: `0023 (head)` listed

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/0023_add_persona_name.py
git commit -m "feat(db): add persona_name column to shop_agents"
```

---

## Task 2: Backend Model + Schemas

**Files:**
- Modify: `backend/src/models/shop_agent.py`
- Modify: `backend/src/api/agents.py`
- Create: `backend/tests/test_api/test_agents.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_api/test_agents.py
import uuid
from unittest.mock import MagicMock


def _make_agent(**kwargs):
    a = MagicMock()
    a.id = kwargs.get('id', uuid.uuid4())
    a.shop_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
    a.name = kwargs.get('name', 'Service Advisor')
    a.role_tagline = kwargs.get('role_tagline', 'Front desk · Customer intake')
    a.accent_color = kwargs.get('accent_color', '#d97706')
    a.initials = kwargs.get('initials', 'SA')
    a.system_prompt = kwargs.get('system_prompt', 'You are the Service Advisor.')
    a.tools = kwargs.get('tools', [])
    a.sort_order = kwargs.get('sort_order', 0)
    a.persona_name = kwargs.get('persona_name', None)
    return a


def test_list_agents_persona_name_present_in_response(client, auth_headers, mock_db):
    agent = _make_agent(persona_name='Tom')
    # _ensure_seeded checks scalar_one_or_none; list query uses scalars().all()
    mock_db.execute.return_value.scalar_one_or_none.return_value = agent
    mock_db.execute.return_value.scalars.return_value.all.return_value = [agent]
    resp = client.get("/agents", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]['persona_name'] == 'Tom'


def test_list_agents_persona_name_null_when_unset(client, auth_headers, mock_db):
    agent = _make_agent(persona_name=None)
    mock_db.execute.return_value.scalar_one_or_none.return_value = agent
    mock_db.execute.return_value.scalars.return_value.all.return_value = [agent]
    resp = client.get("/agents", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()[0]['persona_name'] is None


def test_update_agent_persona_name(client, auth_headers, mock_db):
    agent = _make_agent(persona_name=None)
    mock_db.execute.return_value.scalar_one_or_none.return_value = agent
    resp = client.put(
        f"/agents/{agent.id}",
        json={"persona_name": "Maria"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert agent.persona_name == "Maria"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd backend
python -m pytest tests/test_api/test_agents.py -v
```

Expected: 3 failures — `AgentResponse` has no field `persona_name`

- [ ] **Step 3: Add `persona_name` column to the ORM model**

In `backend/src/models/shop_agent.py`, add after line 18 (`sort_order = Column(...)`):

```python
    persona_name = Column(String, nullable=True)
```

- [ ] **Step 4: Add `persona_name` to Pydantic schemas and `_to_response`**

In `backend/src/api/agents.py`:

Replace the `AgentResponse` class (lines 91–99):
```python
class AgentResponse(BaseModel):
    id: str
    name: str
    role_tagline: str
    accent_color: str
    initials: str
    system_prompt: str
    tools: list[str]
    sort_order: int
    persona_name: Optional[str] = None
```

Replace the `AgentCreate` class (lines 102–109):
```python
class AgentCreate(BaseModel):
    name: str
    role_tagline: str
    accent_color: str = "#d97706"
    initials: str
    system_prompt: str
    tools: list[str] = []
    sort_order: int = 99
    persona_name: Optional[str] = None
```

Replace the `AgentUpdate` class (lines 112–119):
```python
class AgentUpdate(BaseModel):
    name: Optional[str] = None
    role_tagline: Optional[str] = None
    accent_color: Optional[str] = None
    initials: Optional[str] = None
    system_prompt: Optional[str] = None
    tools: Optional[list[str]] = None
    sort_order: Optional[int] = None
    persona_name: Optional[str] = None
```

Replace `_to_response` (lines 122–132):
```python
def _to_response(a: ShopAgent) -> AgentResponse:
    return AgentResponse(
        id=str(a.id),
        name=a.name,
        role_tagline=a.role_tagline,
        accent_color=a.accent_color,
        initials=a.initials,
        system_prompt=a.system_prompt,
        tools=a.tools or [],
        sort_order=a.sort_order,
        persona_name=a.persona_name,
    )
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
cd backend
python -m pytest tests/test_api/test_agents.py -v
```

Expected: 3 tests PASSED

- [ ] **Step 6: Run full backend test suite to check for regressions**

```bash
cd backend
python -m pytest --tb=short -q
```

Expected: all tests pass (new failures = regression, stop and investigate)

- [ ] **Step 7: Commit**

```bash
git add backend/src/models/shop_agent.py backend/src/api/agents.py backend/tests/test_api/test_agents.py
git commit -m "feat(agents): add persona_name field to ShopAgent model and API schemas"
```

---

## Task 3: Frontend Types

**Files:**
- Modify: `web/lib/types.ts:433–468`

- [ ] **Step 1: Add `persona_name` to `ShopAgent`, `AgentCreate`, `AgentUpdate`**

In `web/lib/types.ts`:

Replace the `ShopAgent` interface (lines 433–442):
```typescript
export interface ShopAgent {
  id: string
  name: string
  role_tagline: string
  accent_color: string
  initials: string
  system_prompt: string
  tools: string[]
  sort_order: number
  persona_name?: string | null
}
```

Replace the `AgentCreate` interface (lines 450–458):
```typescript
export interface AgentCreate {
  name: string
  role_tagline: string
  accent_color: string
  initials: string
  system_prompt: string
  tools: string[]
  sort_order?: number
  persona_name?: string | null
}
```

Replace the `AgentUpdate` interface (lines 460–468):
```typescript
export interface AgentUpdate {
  name?: string
  role_tagline?: string
  accent_color?: string
  initials?: string
  system_prompt?: string
  tools?: string[]
  sort_order?: number
  persona_name?: string | null
}
```

- [ ] **Step 2: Verify TypeScript compiles without errors**

```bash
cd web
npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add web/lib/types.ts
git commit -m "feat(types): add persona_name to ShopAgent, AgentCreate, AgentUpdate"
```

---

## Task 4: Settings UI — Persona Name Input

**Files:**
- Modify: `web/app/settings/page.tsx`

The agent edit form lives in a component that starts around line 195. It has state vars for `name`, `tagline`, `color`, `initials`, `prompt`, `selectedTools`.

- [ ] **Step 1: Add `personaName` state and wire it into the save payload**

Find the block starting at line 200:
```typescript
  const [name, setName] = useState(agent?.name ?? '')
  const [tagline, setTagline] = useState(agent?.role_tagline ?? '')
  const [color, setColor] = useState(agent?.accent_color ?? '#d97706')
  const [initials, setInitials] = useState(agent?.initials ?? '')
  const [prompt, setPrompt] = useState(agent?.system_prompt ?? '')
  const [selectedTools, setSelectedTools] = useState<string[]>(agent?.tools ?? [])
  const [showPrompt, setShowPrompt] = useState(false)
```

Add `personaName` after `selectedTools`:
```typescript
  const [name, setName] = useState(agent?.name ?? '')
  const [tagline, setTagline] = useState(agent?.role_tagline ?? '')
  const [color, setColor] = useState(agent?.accent_color ?? '#d97706')
  const [initials, setInitials] = useState(agent?.initials ?? '')
  const [prompt, setPrompt] = useState(agent?.system_prompt ?? '')
  const [selectedTools, setSelectedTools] = useState<string[]>(agent?.tools ?? [])
  const [personaName, setPersonaName] = useState(agent?.persona_name ?? '')
  const [showPrompt, setShowPrompt] = useState(false)
```

Find the `payload` object inside `save` (around line 211):
```typescript
      const payload: AgentCreate = {
        name, role_tagline: tagline, accent_color: color,
        initials, system_prompt: prompt, tools: selectedTools,
      }
```

Replace with:
```typescript
      const payload: AgentCreate = {
        name, role_tagline: tagline, accent_color: color,
        initials, system_prompt: prompt, tools: selectedTools,
        persona_name: personaName || null,
      }
```

- [ ] **Step 2: Add the persona name input field to the form**

The form's JSX starts around line 234. Find the Name/Initials 2-col grid block (around line 244):
```tsx
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
        <div>
          <label style={labelStyle}>Name</label>
          <input value={name} onChange={e => setName(e.target.value)} style={inputStyle} placeholder="e.g. Service Advisor" />
        </div>
        <div>
          <label style={labelStyle}>Initials (2-3 chars)</label>
          <input
            value={initials}
            onChange={e => setInitials(e.target.value.toUpperCase().slice(0, 3))}
            style={inputStyle}
            placeholder="SA"
            maxLength={3}
          />
        </div>
      </div>
```

Add the persona name row immediately after that closing `</div>` and before the Role Tagline row:
```tsx
      <div style={{ marginBottom: '12px' }}>
        <label style={labelStyle}>Persona Name <span style={{ color: '#6b7280', fontWeight: 400, textTransform: 'none' }}>(optional — used for voice, e.g. "Tom")</span></label>
        <input
          value={personaName}
          onChange={e => setPersonaName(e.target.value)}
          style={{ ...inputStyle, maxWidth: '50%' }}
          placeholder="e.g. Tom"
        />
      </div>
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd web
npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 4: Manual browser test**

Start the dev server (`npm run dev` in `web/`). Open `/settings`, go to the Agents tab, click edit on any agent. Verify:
- "Persona Name" field appears below the Name/Initials row
- Typing a name and saving does not error (check Network tab — PUT /agents/{id} should return 200)
- Refreshing the page and re-opening the form shows the saved persona name

- [ ] **Step 5: Commit**

```bash
git add web/app/settings/page.tsx
git commit -m "feat(settings): add persona name input to agent edit form"
```

---

## Task 5: Voice Roster Injection + Name Matching

**Files:**
- Modify: `web/components/VoiceControlWidget.tsx`
- Modify: `web/app/chat/page.tsx:24–34`

### 5a — Dynamic instructions with agent roster

- [ ] **Step 1: Make INSTRUCTIONS dynamic in `VoiceControlWidget.tsx`**

The file currently has `const INSTRUCTIONS = \`...\`` (a static string, lines 10–21) and uses it in `voiceOptions` (line 48).

Replace the static `INSTRUCTIONS` constant and the `agentNames` memo with:

```typescript
const STATIC_INSTRUCTIONS = `You are a voice navigator for an auto shop management app. You control the UI by calling tools. That is your only capability — you cannot answer questions from memory.

Always call a tool. Never respond with text.

Interpret commands broadly:
- "go to reports / customers / inspect / chat" → navigate_to_tab
- "show me / find / do you have [customer name]" → select_customer
- "show me / find / do you have a report for [vehicle or name]" → select_report
- "scroll down / up" → scroll
- "send message / ask [text]" → send_message

If genuinely unsure which tool to use, ask one brief clarifying question.`

const { instructions, agentNames } = useMemo(() => {
  if (!agents?.length) return { instructions: STATIC_INSTRUCTIONS, agentNames: [] as string[] }
  const names: string[] = []
  const rosterLines = agents.map(a => {
    const display = a.persona_name ?? a.name
    names.push(a.name)
    if (a.persona_name) names.push(a.persona_name)
    return `- ${display} (${a.name}) — ${a.role_tagline}`
  })
  const rosterBlock = [
    'Your team members are:',
    ...rosterLines,
    '',
    `When the user addresses any team member by name — "Tom, are you there?", "Hey ${agents[0].persona_name ?? agents[0].name}", or similar — call select_agent with that name immediately, before responding.`,
  ].join('\n')
  return { instructions: `${STATIC_INSTRUCTIONS}\n\n${rosterBlock}`, agentNames: names }
}, [agents])
```

Remove the old `const agentNames = useMemo(...)` line (previously line 27).

In `voiceOptions` (line 48), replace `instructions: INSTRUCTIONS` with `instructions`.

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd web
npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add web/components/VoiceControlWidget.tsx
git commit -m "feat(voice): inject agent roster into voice session instructions"
```

### 5b — Update `registerSelectAgent` to match persona_name

- [ ] **Step 4: Update the name-matching callback in `web/app/chat/page.tsx`**

Find the `useEffect` block at lines 24–34:
```typescript
  useEffect(() => {
    voice.registerSelectAgent((name) => {
      const key = name.toLowerCase()
      const match = agents.find(a =>
        a.name.toLowerCase().includes(key) || key.includes(a.name.toLowerCase())
      )
      if (!match) return false
      setSelectedAgent(match.id)
      return true
    })
  }, [voice, agents])
```

Replace with:
```typescript
  useEffect(() => {
    voice.registerSelectAgent((name) => {
      const key = name.toLowerCase()
      const match = agents.find(a => {
        const roleName = a.name.toLowerCase()
        const personaName = (a.persona_name ?? '').toLowerCase()
        return roleName.includes(key) || key.includes(roleName)
          || (personaName && (personaName.includes(key) || key.includes(personaName)))
      })
      if (!match) return false
      setSelectedAgent(match.id)
      return true
    })
  }, [voice, agents])
```

- [ ] **Step 5: Verify TypeScript compiles**

```bash
cd web
npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 6: Manual voice test**

In `/settings`, set persona_name "Tom" on the Service Advisor. Open `/chat`, activate the voice widget, say "Tom, are you there?" Verify the active agent switches to Service Advisor.

- [ ] **Step 7: Commit**

```bash
git add web/app/chat/page.tsx
git commit -m "feat(voice): match agent selection by persona_name in addition to role name"
```

---

## Task 6: Chat Header — Show Real Agent Name + Role

**Files:**
- Modify: `web/app/chat/page.tsx`
- Modify: `web/components/chat/ChatPanel.tsx`

### 6a — Pass active agent object to ChatPanel

- [ ] **Step 1: Derive `activeAgent` and pass it as a prop in `web/app/chat/page.tsx`**

The page currently renders:
```tsx
        {selectedAgent && (
          <ChatPanel
            key={selectedAgent}
            agentId={selectedAgent}
            onNewMessage={(text) =>
              setLastMessages(prev => ({ ...prev, [selectedAgent]: text }))
            }
          />
        )}
```

Replace with:
```tsx
        {selectedAgent && (
          <ChatPanel
            key={selectedAgent}
            agentId={selectedAgent}
            agent={agents.find(a => a.id === selectedAgent)}
            onNewMessage={(text) =>
              setLastMessages(prev => ({ ...prev, [selectedAgent]: text }))
            }
          />
        )}
```

### 6b — Update ChatPanel header

- [ ] **Step 2: Add `agent` prop and fix the header in `web/components/chat/ChatPanel.tsx`**

Add `ShopAgent` import at the top of the file. The file already imports from `@/lib/api`; add the type import:
```typescript
import type { ShopAgent } from '@/lib/types'
```

Replace the `Props` interface (lines 35–38):
```typescript
interface Props {
  agentId: string
  agent?: ShopAgent
  onNewMessage: (text: string) => void
}
```

Replace the function signature (line 40):
```typescript
export function ChatPanel({ agentId, agent, onNewMessage }: Props) {
```

Remove the `AGENT_NAMES` constant entirely (line 18):
```typescript
const AGENT_NAMES: Record<string, string> = { assistant: 'Assistant', tom: 'Tom' }
```
(delete this line)

Replace the header block (lines 184–196):
```tsx
        {/* Header */}
        <div
          className="flex-shrink-0 px-5 py-3 flex items-center gap-2.5"
          style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
        >
          {agent?.accent_color && (
            <div
              className="w-2 h-2 rounded-full flex-shrink-0"
              style={{ background: agent.accent_color }}
            />
          )}
          <div className="flex flex-col min-w-0 flex-1">
            <span className="font-semibold text-sm text-white leading-tight">
              {agent?.persona_name ?? agent?.name ?? agentId}
            </span>
            {agent?.role_tagline && (
              <span className="text-[10px] leading-tight" style={{ color: 'rgba(255,255,255,0.35)' }}>
                {agent.role_tagline}
              </span>
            )}
          </div>
          <span
            className="text-[10px] px-1.5 py-0.5 rounded-full flex-shrink-0"
            style={{ background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.35)' }}
          >
            AI
          </span>
        </div>
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd web
npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 4: Manual browser test**

Open `/chat`. Verify:
- The header shows the agent name (or persona name if set) with its role tagline below it
- The accent color dot matches the agent's color
- Clicking different agents in the sidebar updates the header immediately
- If persona name "Tom" is set on Service Advisor, the header shows "Tom" with "Front desk · Customer intake" below
- The voice widget switching agents also updates the header

- [ ] **Step 5: Commit**

```bash
git add web/app/chat/page.tsx web/components/chat/ChatPanel.tsx
git commit -m "feat(chat): show active agent persona name and role tagline in chat header"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** All 4 spec parts covered: migration (Task 1), settings UI (Task 4), voice injection + matching (Task 5), chat header fix (Task 6)
- [x] **No placeholders:** All steps contain actual code
- [x] **Type consistency:** `persona_name` is `Optional[str]` in Python, `string | null | undefined` in TypeScript throughout — consistent
- [x] **Task ordering:** Migration → model → types → UI → voice → header (each task can build on prior)
