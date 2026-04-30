# Voice Layer + Report Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add global voice control (navigate tabs, select agents, send messages, open customer/report records) and polish the Reports page to match iOS visual quality.

**Architecture:** A `VoiceContext` holds cross-component callbacks for agent selection and message sending. A `VoiceControlWidget` in the nav bar owns the WebRTC session via `useVoiceControl` and dispatches 5 voice tools — navigation and customer/report selection go through `router.push()` directly (including URL params for cross-page selection), while agent selection and message sending go through the context. The Reports page gets glass-card sections, severity icons, labor-hour sub-lines, and accent colors.

**Tech Stack:** OpenAI Realtime API (gpt-4o-mini-realtime-preview), WebRTC, zod, Next.js Route Handler, React Context + refs

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Install | `npm install zod` | Zod schema parsing for voice tools |
| Create | `web/lib/voice/types.ts` | All TypeScript types for voice library |
| Create | `web/lib/voice/schema.ts` | Zod schema normalization helpers |
| Create | `web/lib/voice/defineVoiceTool.ts` | Tool definition factory |
| Create | `web/lib/voice/transport/types.ts` | Transport interface types |
| Create | `web/lib/voice/transport/webRtcRealtimeTransport.ts` | WebRTC peer + data channel logic |
| Create | `web/lib/voice/internal/session.ts` | Session payload builder |
| Create | `web/lib/voice/voiceControlController.ts` | State machine + tool dispatch |
| Create | `web/lib/voice/useVoiceControl.ts` | React hook wrapping the controller |
| Create | `web/app/api/session/route.ts` | Server route — exchanges API key for ephemeral token |
| Create | `web/contexts/VoiceContext.tsx` | Global context for selectAgent + sendMessage callbacks |
| Create | `web/lib/voice/tools.ts` | Factory for 5 voice tool definitions |
| Create | `web/components/VoiceControlWidget.tsx` | Mic button + status ring + PTT toggle |
| Modify | `web/app/providers.tsx` | Wrap tree with VoiceProvider |
| Modify | `web/components/AppShell.tsx` | Add VoiceControlWidget to nav |
| Modify | `web/app/chat/page.tsx` | Register selectAgent callback |
| Modify | `web/components/chat/ChatPanel.tsx` | Register sendMessage callback + report chip |
| Modify | `web/app/customers/page.tsx` | Read voice_select param, auto-select customer |
| Modify | `web/app/reports/page.tsx` | Read voice_select param + all visual polish |

---

## Task 1: Install zod and copy voice library files

**Files:**
- Create: `web/lib/voice/types.ts`
- Create: `web/lib/voice/schema.ts`
- Create: `web/lib/voice/defineVoiceTool.ts`
- Create: `web/lib/voice/transport/types.ts`
- Create: `web/lib/voice/transport/webRtcRealtimeTransport.ts`
- Create: `web/lib/voice/internal/session.ts`
- Create: `web/lib/voice/voiceControlController.ts`
- Create: `web/lib/voice/useVoiceControl.ts`

- [ ] **Step 1: Install zod**

```bash
cd web
npm install zod
```

Expected: `added 1 package` (or similar)

- [ ] **Step 2: Create `web/lib/voice/types.ts`**

Copy verbatim from `/Users/joehe/workspace/learning/realtime-voice-component/src/types.ts`. No path changes needed.

- [ ] **Step 3: Create `web/lib/voice/schema.ts`**

```ts
import { toJSONSchema } from "zod";
import type { JsonSchema, ZodLikeSchema } from "./types";

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function isZodSchema(schema: unknown): schema is ZodLikeSchema {
  return isPlainObject(schema) && "safeParse" in schema && typeof schema.safeParse === "function";
}

function stripSchemaMetadata(schema: JsonSchema): JsonSchema {
  const { $schema, definitions, $ref, ...rest } = schema;
  if (typeof $ref === "string" && definitions && typeof definitions === "object") {
    const key = $ref.split("/").at(-1);
    const definitionMap = definitions as Record<string, unknown>;
    if (key && key in definitionMap) {
      return stripSchemaMetadata(definitionMap[key] as JsonSchema);
    }
  }
  return rest;
}

export function normalizeToolSchema(schema: ZodLikeSchema): JsonSchema {
  return stripSchemaMetadata(toJSONSchema(schema as never) as JsonSchema);
}

export function parseToolArguments<TArgs>(schema: ZodLikeSchema<TArgs>, rawArgs: string): TArgs {
  const parsed = rawArgs.trim().length === 0 ? {} : JSON.parse(rawArgs);
  return schema.parse(parsed) as TArgs;
}
```

- [ ] **Step 4: Create `web/lib/voice/defineVoiceTool.ts`**

```ts
import { isZodSchema, normalizeToolSchema, parseToolArguments } from "./schema";
import type { VoiceTool, VoiceToolDefinition } from "./types";

export function defineVoiceTool<TArgs>(definition: VoiceToolDefinition<TArgs>): VoiceTool<TArgs> {
  if (!isZodSchema(definition.parameters)) {
    throw new Error("Pass a Zod schema to defineVoiceTool().");
  }
  const jsonSchema = normalizeToolSchema(definition.parameters);
  return {
    ...definition,
    jsonSchema,
    realtimeTool: {
      type: "function",
      name: definition.name,
      description: definition.description,
      parameters: jsonSchema,
    },
    parseArguments(rawArgs: string) {
      return parseToolArguments<TArgs>(definition.parameters, rawArgs);
    },
  };
}
```

- [ ] **Step 5: Create `web/lib/voice/transport/types.ts`**

Copy verbatim from `/Users/joehe/workspace/learning/realtime-voice-component/src/transport/types.ts`. Import paths (`../types`) are correct as-is.

- [ ] **Step 6: Create `web/lib/voice/internal/session.ts`**

Copy verbatim from `/Users/joehe/workspace/learning/realtime-voice-component/src/internal/session.ts`. Import paths (`../types`, `../transport/types`) are correct as-is.

- [ ] **Step 7: Create `web/lib/voice/transport/webRtcRealtimeTransport.ts`**

Copy verbatim from `/Users/joehe/workspace/learning/realtime-voice-component/src/transport/webRtcRealtimeTransport.ts`. Import paths (`../internal/session`, `../types`, `./types`) are correct as-is.

- [ ] **Step 8: Create `web/lib/voice/voiceControlController.ts`**

Copy verbatim from `/Users/joehe/workspace/learning/realtime-voice-component/src/voiceControlController.ts`. Change only the default model string on line 23:

```ts
// Change this line:
const DEFAULT_MODEL = "gpt-realtime-1.5";
// To:
const DEFAULT_MODEL = "gpt-4o-mini-realtime-preview";
```

All import paths (`./transport/webRtcRealtimeTransport`, `./types`) are correct as-is.

- [ ] **Step 9: Create `web/lib/voice/useVoiceControl.ts`**

Copy verbatim from `/Users/joehe/workspace/learning/realtime-voice-component/src/useVoiceControl.ts`. Import paths (`./voiceControlController`, `./types`) are correct as-is.

- [ ] **Step 10: Verify TypeScript compiles**

```bash
cd web
npx tsc --noEmit 2>&1 | head -30
```

Expected: No errors in `lib/voice/` files. (Ignore unrelated pre-existing errors if any.)

- [ ] **Step 11: Commit**

```bash
cd web
git add lib/voice/ package.json package-lock.json
git commit -m "feat(voice): copy voice control library and install zod"
```

---

## Task 2: Create `/api/session` route

**Files:**
- Create: `web/app/api/session/route.ts`

- [ ] **Step 1: Create the route file**

```ts
import { NextResponse } from 'next/server'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const model = searchParams.get('model') ?? 'gpt-4o-mini-realtime-preview'

  const res = await fetch('https://api.openai.com/v1/realtime/sessions', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ model, voice: 'alloy' }),
  })

  if (!res.ok) {
    const text = await res.text()
    return NextResponse.json({ error: text }, { status: res.status })
  }

  const data = await res.json()
  return NextResponse.json(data)
}
```

- [ ] **Step 2: Start dev server and verify with curl**

```bash
cd web
npm run dev &
sleep 5
curl -s "http://localhost:3000/api/session" | python3 -m json.tool | grep -E "client_secret|error"
```

Expected output contains `"client_secret"` with a `"value"` field. If you see `"error"`, check that `OPENAI_API_KEY` is set in `web/.env.local`.

- [ ] **Step 3: Commit**

```bash
git add web/app/api/session/route.ts
git commit -m "feat(voice): add /api/session route for ephemeral token"
```

---

## Task 3: Create VoiceContext

**Files:**
- Create: `web/contexts/VoiceContext.tsx`

- [ ] **Step 1: Create the context**

```tsx
'use client'
import { createContext, useContext, useRef, useMemo } from 'react'

type VoiceContextValue = {
  registerSelectAgent: (fn: (name: string) => boolean) => void
  registerSendMessage: (fn: (text: string) => void) => void
  selectAgent: (name: string) => boolean
  sendMessage: (text: string) => void
}

const VoiceContext = createContext<VoiceContextValue | null>(null)

export function VoiceProvider({ children }: { children: React.ReactNode }) {
  const fns = useRef({
    selectAgent: null as ((name: string) => boolean) | null,
    sendMessage: null as ((text: string) => void) | null,
  }).current

  const value = useMemo<VoiceContextValue>(() => ({
    registerSelectAgent: fn => { fns.selectAgent = fn },
    registerSendMessage: fn => { fns.sendMessage = fn },
    selectAgent: name => fns.selectAgent?.(name) ?? false,
    sendMessage: text => fns.sendMessage?.(text),
  }), []) // eslint-disable-line react-hooks/exhaustive-deps

  return <VoiceContext.Provider value={value}>{children}</VoiceContext.Provider>
}

export function useVoiceContext() {
  const ctx = useContext(VoiceContext)
  if (!ctx) throw new Error('useVoiceContext must be used within VoiceProvider')
  return ctx
}
```

- [ ] **Step 2: Commit**

```bash
git add web/contexts/VoiceContext.tsx
git commit -m "feat(voice): add VoiceContext for cross-component callbacks"
```

---

## Task 4: Create voice tools and VoiceControlWidget

**Files:**
- Create: `web/lib/voice/tools.ts`
- Create: `web/components/VoiceControlWidget.tsx`

- [ ] **Step 1: Create `web/lib/voice/tools.ts`**

```ts
import { z } from 'zod'
import { defineVoiceTool } from './defineVoiceTool'
import type { VoiceTool } from './types'

const TAB_VALUES = ['customers', 'reports', 'inspect', 'chat'] as const

const TAB_ROUTES: Record<string, string> = {
  customers: '/customers',
  reports: '/reports',
  inspect: '/inspect',
  chat: '/chat',
}

export function createVoiceTools(dispatchers: {
  navigate: (path: string) => void
  selectAgent: (name: string) => boolean
  sendMessage: (text: string) => void
  selectCustomer: (name: string) => void
  selectReport: (query: string) => void
}): VoiceTool[] {
  return [
    defineVoiceTool({
      name: 'navigate_to_tab',
      description: 'Navigate to one of the four main tabs: customers, reports, inspect, or chat.',
      parameters: z.object({
        tab: z.enum(TAB_VALUES).describe('The tab to navigate to'),
      }),
      execute: ({ tab }) => {
        dispatchers.navigate(TAB_ROUTES[tab])
        return { ok: true, tab }
      },
    }),
    defineVoiceTool({
      name: 'select_agent',
      description: 'Select a chat agent by name. Available agents are "Assistant" and "Tom".',
      parameters: z.object({
        name: z.string().describe('Agent name, e.g. "Assistant" or "Tom"'),
      }),
      execute: ({ name }) => {
        const ok = dispatchers.selectAgent(name)
        return ok ? { ok: true } : { ok: false, message: `No agent found matching "${name}". Available: Assistant, Tom.` }
      },
    }),
    defineVoiceTool({
      name: 'send_message',
      description: 'Send a message to the currently selected agent in the chat panel.',
      parameters: z.object({
        text: z.string().describe('The message to send'),
      }),
      execute: ({ text }) => {
        dispatchers.sendMessage(text)
        return { ok: true }
      },
    }),
    defineVoiceTool({
      name: 'select_customer',
      description: 'Navigate to the Customers tab and open a customer record by name.',
      parameters: z.object({
        name: z.string().describe('Customer name or partial name, e.g. "John Smith" or "Smith"'),
      }),
      execute: ({ name }) => {
        dispatchers.selectCustomer(name)
        return { ok: true, searching: name }
      },
    }),
    defineVoiceTool({
      name: 'select_report',
      description: 'Navigate to the Reports tab and open a report by vehicle name or description.',
      parameters: z.object({
        query: z.string().describe('Vehicle name or partial description, e.g. "Civic" or "2019 Honda"'),
      }),
      execute: ({ query }) => {
        dispatchers.selectReport(query)
        return { ok: true, searching: query }
      },
    }),
  ]
}
```

- [ ] **Step 2: Create `web/components/VoiceControlWidget.tsx`**

```tsx
'use client'
import { useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useVoiceControl } from '@/lib/voice/useVoiceControl'
import { createVoiceTools } from '@/lib/voice/tools'
import { useVoiceContext } from '@/contexts/VoiceContext'
import type { ActivationMode } from '@/lib/voice/types'

const INSTRUCTIONS = `You are a voice control assistant for an auto shop management web app.
Use the registered tools to control the UI. When the user says to navigate, select, or send — call the matching tool immediately.
Do not chat. If a required argument is unclear, ask one brief question.`

export function VoiceControlWidget() {
  const router = useRouter()
  const context = useVoiceContext()
  const [activationMode, setActivationMode] = useState<ActivationMode>('vad')

  const tools = useMemo(() => createVoiceTools({
    navigate: path => router.push(path),
    selectAgent: name => context.selectAgent(name),
    sendMessage: text => context.sendMessage(text),
    selectCustomer: name => router.push(`/customers?voice_select=${encodeURIComponent(name)}`),
    selectReport: query => router.push(`/reports?voice_select=${encodeURIComponent(query)}`),
  }), [context, router])

  const controller = useVoiceControl({
    auth: { tokenEndpoint: '/api/session' },
    tools,
    instructions: INSTRUCTIONS,
    model: 'gpt-4o-mini-realtime-preview',
    activationMode,
    outputMode: 'tool-only',
  })

  const { status, connect, disconnect, startCapture, stopCapture } = controller
  const isConnected = status !== 'idle' && status !== 'error' && status !== 'connecting'

  const ringStyle = {
    idle: '0 0 0 2px rgba(255,255,255,0.12)',
    connecting: '0 0 0 2px var(--accent)',
    ready: '0 0 0 2px rgba(74,222,128,0.5)',
    listening: '0 0 0 2px rgba(74,222,128,0.9)',
    processing: '0 0 0 2px var(--accent)',
    error: '0 0 0 2px rgba(239,68,68,0.9)',
  }[status] ?? '0 0 0 2px rgba(255,255,255,0.12)'

  function handleClick() {
    if (status === 'idle' || status === 'error') { connect(); return }
    if (activationMode === 'vad') { disconnect(); return }
  }

  return (
    <div className="flex items-center gap-1.5">
      <button
        onClick={handleClick}
        onMouseDown={activationMode === 'push-to-talk' && isConnected ? () => startCapture() : undefined}
        onMouseUp={activationMode === 'push-to-talk' && isConnected ? () => stopCapture() : undefined}
        onTouchStart={activationMode === 'push-to-talk' && isConnected ? (e) => { e.preventDefault(); startCapture() } : undefined}
        onTouchEnd={activationMode === 'push-to-talk' && isConnected ? () => stopCapture() : undefined}
        title={
          status === 'idle' ? 'Enable voice control'
          : status === 'error' ? 'Voice error — click to retry'
          : status === 'connecting' ? 'Connecting…'
          : status === 'listening' ? (activationMode === 'push-to-talk' ? 'Hold to speak' : 'Listening…')
          : status === 'processing' ? 'Processing…'
          : 'Click to disconnect'
        }
        className="w-7 h-7 rounded-full flex items-center justify-center transition-all select-none"
        style={{ background: 'rgba(255,255,255,0.06)', boxShadow: ringStyle }}
      >
        {status === 'connecting' ? (
          <div className="w-2.5 h-2.5 rounded-full animate-pulse" style={{ background: 'var(--accent)' }} />
        ) : (
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
            stroke={isConnected ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.35)'}
            strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" y1="19" x2="12" y2="22"/>
          </svg>
        )}
      </button>

      {isConnected && (
        <button
          onClick={() => setActivationMode(m => m === 'vad' ? 'push-to-talk' : 'vad')}
          title={activationMode === 'vad' ? 'Switch to push-to-talk' : 'Switch to always-listening'}
          className="text-[9px] px-1.5 py-0.5 rounded transition-colors select-none"
          style={{
            background: activationMode === 'push-to-talk' ? 'var(--accent)' : 'rgba(255,255,255,0.07)',
            color: activationMode === 'push-to-talk' ? '#fff' : 'rgba(255,255,255,0.3)',
          }}
        >
          PTT
        </button>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add web/lib/voice/tools.ts web/components/VoiceControlWidget.tsx
git commit -m "feat(voice): add voice tools and VoiceControlWidget"
```

---

## Task 5: Wire VoiceProvider and VoiceControlWidget into the app shell

**Files:**
- Modify: `web/app/providers.tsx`
- Modify: `web/components/AppShell.tsx`

- [ ] **Step 1: Read current providers.tsx**

```bash
cat web/app/providers.tsx
```

- [ ] **Step 2: Add VoiceProvider to `web/app/providers.tsx`**

Wrap the existing tree with `<VoiceProvider>`. The file currently looks like:

```tsx
'use client'
import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@/components/ThemeProvider'

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient())
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>{children}</ThemeProvider>
    </QueryClientProvider>
  )
}
```

Change it to:

```tsx
'use client'
import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@/components/ThemeProvider'
import { VoiceProvider } from '@/contexts/VoiceContext'

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient())
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <VoiceProvider>{children}</VoiceProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
```

- [ ] **Step 3: Add VoiceControlWidget to `web/components/AppShell.tsx`**

Add the import and insert `<VoiceControlWidget />` in the nav bar, between the nav links and the user avatar button. Current nav tail:

```tsx
        <button
          onClick={handleLogout}
          title="Log out"
          className="ml-auto w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold transition-colors"
          style={{ background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.6)' }}
        >
          {initials}
        </button>
```

Add the import at the top:
```tsx
import { VoiceControlWidget } from './VoiceControlWidget'
```

And insert the widget just before the logout button:
```tsx
        <div className="ml-auto flex items-center gap-2">
          <VoiceControlWidget />
          <button
            onClick={handleLogout}
            title="Log out"
            className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold transition-colors"
            style={{ background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.6)' }}
          >
            {initials}
          </button>
        </div>
```

(Remove `ml-auto` from the logout button since it's now on the wrapping div.)

- [ ] **Step 4: Verify in browser**

Open `http://localhost:3000/chat` (dev server must be running). You should see a small mic icon in the top-right nav bar next to the avatar button. Clicking it should show a connecting animation, then a green ring when VAD is active.

- [ ] **Step 5: Commit**

```bash
git add web/app/providers.tsx web/components/AppShell.tsx
git commit -m "feat(voice): wire VoiceProvider and VoiceControlWidget into app shell"
```

---

## Task 6: Register agent selection and message sending in chat

**Files:**
- Modify: `web/app/chat/page.tsx`
- Modify: `web/components/chat/ChatPanel.tsx`

- [ ] **Step 1: Update `web/app/chat/page.tsx` to register selectAgent**

Current file:
```tsx
'use client'
import { useState } from 'react'
import { AppShell } from '@/components/AppShell'
import { AgentList } from '@/components/chat/AgentList'
import { ChatPanel } from '@/components/chat/ChatPanel'

export default function ChatPage() {
  const [selectedAgent, setSelectedAgent] = useState('assistant')
  const [lastMessages, setLastMessages] = useState<Record<string, string>>({})

  return (
    <AppShell>
      <div className="flex h-full">
        <AgentList
          selectedId={selectedAgent}
          onSelect={setSelectedAgent}
          lastMessages={lastMessages}
        />
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
    </AppShell>
  )
}
```

Change to:
```tsx
'use client'
import { useEffect, useState } from 'react'
import { AppShell } from '@/components/AppShell'
import { AgentList } from '@/components/chat/AgentList'
import { ChatPanel } from '@/components/chat/ChatPanel'
import { useVoiceContext } from '@/contexts/VoiceContext'

const AGENT_IDS: Record<string, string> = {
  assistant: 'assistant',
  tom: 'tom',
}

export default function ChatPage() {
  const [selectedAgent, setSelectedAgent] = useState('assistant')
  const [lastMessages, setLastMessages] = useState<Record<string, string>>({})
  const voice = useVoiceContext()

  useEffect(() => {
    voice.registerSelectAgent((name) => {
      const key = name.toLowerCase()
      const id = Object.entries(AGENT_IDS).find(([agentId, _]) =>
        agentId.includes(key) || key.includes(agentId)
      )?.[0]
      if (!id) return false
      setSelectedAgent(id)
      return true
    })
  }, [voice])

  return (
    <AppShell>
      <div className="flex h-full">
        <AgentList
          selectedId={selectedAgent}
          onSelect={setSelectedAgent}
          lastMessages={lastMessages}
        />
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
    </AppShell>
  )
}
```

- [ ] **Step 2: Add registerSendMessage and report chip to `web/components/chat/ChatPanel.tsx`**

**2a.** Add import at the top of ChatPanel.tsx (after existing imports):
```tsx
import { useVoiceContext } from '@/contexts/VoiceContext'
```

**2b.** Inside the `ChatPanel` function body, after the existing `useState` declarations, add:
```tsx
  const voice = useVoiceContext()

  useEffect(() => {
    voice.registerSendMessage((text) => {
      handleSend(text)
    })
  }, [voice]) // eslint-disable-line react-hooks/exhaustive-deps
```

Note: `handleSend` is defined later in the same function. This is safe because the effect runs after mount, at which point `handleSend` is defined and stable enough in the closure. The eslint-disable is needed because `handleSend` is not in the dep array (it recreates every render; adding it would re-register every render which is wasteful but not incorrect).

**2c.** Add a `reportId` state that tracks when a report is generated. After the existing `quoteId` state:
```tsx
  const [reportId, setReportId] = useState<string | null>(null)
```

**2d.** In the existing `useEffect` that scans `history` for `quote_id`, extend it to also look for `report_id`:
```tsx
  useEffect(() => {
    if (agentId !== 'assistant' || quoteId) return
    for (let i = history.length - 1; i >= 0; i--) {
      const msg = history[i]
      if (msg.tool_calls) {
        const hit = msg.tool_calls.find(
          tc => tc.name === 'create_quote' && typeof tc.output?.quote_id === 'string'
        )
        if (hit) {
          setQuoteId(hit.output.quote_id as string)
          break
        }
      }
    }
  }, [history, agentId, quoteId])

  useEffect(() => {
    if (agentId !== 'assistant') return
    for (let i = history.length - 1; i >= 0; i--) {
      const msg = history[i]
      if (msg.tool_calls) {
        const hit = msg.tool_calls.find(
          tc => typeof tc.output?.report_id === 'string'
        )
        if (hit) {
          setReportId(hit.output.report_id as string)
          return
        }
      }
    }
  }, [history, agentId])
```

**2e.** Also detect `report_id` in streaming tool_end events. In the `handleSend` function, find this block:
```tsx
          if (te.output && typeof te.output.quote_id === 'string') {
            setQuoteId(te.output.quote_id)
          }
```

Add immediately after it:
```tsx
          if (te.output && typeof te.output.report_id === 'string') {
            setReportId(te.output.report_id)
          }
```

**2f.** Add the "View Report" chip in the JSX. Find the `<QuoteSummary />` element (or the end of the messages area) and add a chip when `reportId` is set. Locate the section just above the input bar and add:

```tsx
        {reportId && (
          <div className="px-5 pb-3">
            <a
              href={`/reports?id=${reportId}`}
              className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full transition-colors"
              style={{ background: 'color-mix(in srgb, var(--accent) 12%, transparent)', color: 'var(--accent)', border: '1px solid color-mix(in srgb, var(--accent) 30%, transparent)' }}
            >
              📋 View Report →
            </a>
          </div>
        )}
```

- [ ] **Step 3: Test voice agent selection**

With the dev server running, navigate to `/chat`. Click the mic button (VAD mode). Say "select Tom". The sidebar should switch to Tom. Say "go back to Assistant". Should switch back.

- [ ] **Step 4: Test send message**

With mic connected, say "send a message: check the brake pads on a 2019 Honda Civic". The message should appear in the chat input and be sent.

- [ ] **Step 5: Commit**

```bash
git add web/app/chat/page.tsx web/components/chat/ChatPanel.tsx
git commit -m "feat(voice): register agent selection and message sending; add report chip"
```

---

## Task 7: Voice-select customer by URL param

**Files:**
- Modify: `web/app/customers/page.tsx`

The current `CustomersPage` function doesn't use `useSearchParams`. We need to add Suspense (required by Next.js App Router when using `useSearchParams`) and auto-select the customer when `voice_select` param is present.

- [ ] **Step 1: Read the full current customers page**

```bash
cat web/app/customers/page.tsx
```

- [ ] **Step 2: Add voice_select support**

At the top of the file, add the import:
```tsx
import { useSearchParams } from 'next/navigation'
import { Suspense } from 'react'
```

Rename `CustomersPage` to `CustomersPageInner` and add a `useEffect` inside it:

After the existing `const filtered = customers.filter(...)` line, add:
```tsx
  const searchParams = useSearchParams()
  const voiceSelect = searchParams.get('voice_select')

  useEffect(() => {
    if (!voiceSelect || customers.length === 0) return
    const q = voiceSelect.toLowerCase()
    const match = customers.find(c => c.name.toLowerCase().includes(q))
    if (match) setSelectedId(match.customer_id)
  }, [voiceSelect, customers])
```

Then export a new default `CustomersPage` that wraps in Suspense:
```tsx
export default function CustomersPage() {
  return (
    <Suspense>
      <CustomersPageInner />
    </Suspense>
  )
}
```

And change the existing `export default function CustomersPage()` to `function CustomersPageInner()`.

- [ ] **Step 3: Test**

In browser, navigate to `http://localhost:3000/customers?voice_select=smith`. Verify the first customer whose name contains "smith" is auto-selected.

- [ ] **Step 4: Test via voice**

With mic connected, say "open John Smith". You should be navigated to `/customers?voice_select=John+Smith` and the customer auto-selected.

- [ ] **Step 5: Commit**

```bash
git add web/app/customers/page.tsx
git commit -m "feat(voice): auto-select customer from voice_select URL param"
```

---

## Task 8: Reports page — visual polish and voice_select support

**Files:**
- Modify: `web/app/reports/page.tsx`

This task rewrites the reports page content. Read the current file first, then make all changes in one pass.

- [ ] **Step 1: Read current file**

```bash
cat web/app/reports/page.tsx
```

- [ ] **Step 2: Rewrite `web/app/reports/page.tsx`**

Replace the entire file with the following. Key changes from the original:
- `voice_select` param auto-selects a report (same pattern as customers)
- Glass-card sections (each section card has `rgba(255,255,255,0.03)` bg + `rgba(255,255,255,0.07)` border)
- `var(--accent)` for grand total and active report list item
- Severity icons (`✕` red, `⚠` amber, `✓` green) with proper colors
- Labor hours sub-line in estimate rows
- Report list active state uses accent color

```tsx
'use client'

import { useState, useEffect, Suspense } from 'react'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'next/navigation'
import { AppShell } from '@/components/AppShell'
import { getAllReports, getReport } from '@/lib/api'
import type { ReportSummary, ReportDetail, Finding } from '@/lib/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function severityIcon(s: string) {
  switch ((s ?? '').toLowerCase()) {
    case 'high':
    case 'urgent':
      return { icon: '✕', color: '#f87171' }  // red-400
    case 'medium':
    case 'moderate':
      return { icon: '⚠', color: '#fb923c' }  // orange-400
    default:
      return { icon: '✓', color: '#4ade80' }  // green-400
  }
}

function FindingCard({ f }: { f: Finding }) {
  const { icon, color } = severityIcon(f.severity)
  return (
    <div
      className="rounded-xl p-4"
      style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}
    >
      <div className="flex items-start gap-3 mb-2">
        <span className="text-base leading-none mt-0.5 flex-shrink-0" style={{ color }}>{icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm font-semibold text-white">{f.part}</p>
            <span
              className="text-[10px] font-semibold px-2 py-0.5 rounded-full flex-shrink-0"
              style={{ background: `${color}18`, color }}
            >
              {f.severity}
            </span>
          </div>
          <p className="text-sm mt-1 leading-relaxed" style={{ color: 'rgba(255,255,255,0.5)' }}>{f.notes}</p>
        </div>
      </div>
      {f.photo_url && (
        <img
          src={f.photo_url}
          alt={f.part}
          className="mt-2 w-full max-h-52 object-cover rounded-lg"
          style={{ border: '1px solid rgba(255,255,255,0.07)' }}
        />
      )}
    </div>
  )
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-widest mb-2 px-0.5" style={{ color: 'rgba(255,255,255,0.3)' }}>
        {title}
      </p>
      <div
        className="rounded-xl p-4"
        style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)' }}
      >
        {children}
      </div>
    </div>
  )
}

function vehicleLabel(r: ReportSummary): string {
  const v = r.vehicle
  if (!v || (!v.year && !v.make)) return 'Unknown Vehicle'
  return [v.year, v.make, v.model].filter(Boolean).join(' ')
}

function formatCurrency(n: number): string {
  return n === 0 ? '—' : `$${n.toFixed(2)}`
}

function ReportsPageInner() {
  const searchParams = useSearchParams()
  const vehicleFilter = searchParams.get('vehicle')
  const preselectedId = searchParams.get('id')
  const voiceSelect = searchParams.get('voice_select')
  const [selectedId, setSelectedId] = useState<string | null>(preselectedId)

  const { data: reports = [], isLoading } = useQuery<ReportSummary[]>({
    queryKey: ['reports'],
    queryFn: getAllReports,
  })

  const { data: detail, isLoading: detailLoading } = useQuery<ReportDetail>({
    queryKey: ['report', selectedId],
    queryFn: () => getReport(selectedId!),
    enabled: !!selectedId,
  })

  useEffect(() => {
    if (!voiceSelect || reports.length === 0) return
    const q = voiceSelect.toLowerCase()
    const match = reports.find(r => vehicleLabel(r).toLowerCase().includes(q))
    if (match) setSelectedId(match.id)
  }, [voiceSelect, reports])

  const displayed = vehicleFilter
    ? reports.filter(r => r.vehicle?.vehicle_id === vehicleFilter)
    : reports

  return (
    <AppShell>
      <div className="flex h-full overflow-hidden">
        {/* Left panel: report list */}
        <div
          className="w-64 flex-shrink-0 flex flex-col"
          style={{ background: 'rgba(255,255,255,0.015)', borderRight: '1px solid rgba(255,255,255,0.07)' }}
        >
          <div
            className="p-3 flex items-center gap-2"
            style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
          >
            <span className="text-sm font-semibold text-white flex-1">Reports</span>
            {vehicleFilter && (
              <Link href="/reports" className="text-xs" style={{ color: 'var(--accent)' }}>
                clear filter
              </Link>
            )}
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
            {isLoading && (
              <p className="text-xs px-2 py-3" style={{ color: 'rgba(255,255,255,0.3)' }}>Loading…</p>
            )}
            {displayed.map(r => {
              const active = selectedId === r.id
              return (
                <button
                  key={r.id}
                  onClick={() => setSelectedId(r.id)}
                  className="w-full text-left px-3 py-2.5 rounded-lg transition-colors"
                  style={active ? {
                    background: 'rgba(255,255,255,0.06)',
                    borderLeft: '2px solid var(--accent)',
                    paddingLeft: '10px',
                  } : {
                    borderLeft: '2px solid transparent',
                    paddingLeft: '10px',
                  }}
                >
                  <p className="text-xs font-semibold text-white truncate">{vehicleLabel(r)}</p>
                  <p className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.35)' }}>
                    {r.created_at ? new Date(r.created_at).toLocaleDateString() : '—'}
                    {r.total ? ` · $${r.total.toFixed(0)}` : ''}
                  </p>
                </button>
              )
            })}
            {!isLoading && displayed.length === 0 && (
              <p className="text-xs px-2 py-4 text-center" style={{ color: 'rgba(255,255,255,0.25)' }}>No reports</p>
            )}
          </div>
        </div>

        {/* Right panel: report detail */}
        <div className="flex-1 overflow-y-auto" style={{ background: '#030712' }}>
          {!selectedId ? (
            <div className="flex h-full items-center justify-center text-sm" style={{ color: 'rgba(255,255,255,0.2)' }}>
              Select a report
            </div>
          ) : detailLoading ? (
            <div className="flex h-full items-center justify-center text-sm" style={{ color: 'rgba(255,255,255,0.3)' }}>
              Loading…
            </div>
          ) : detail ? (
            <div className="p-6 max-w-3xl space-y-5">
              {/* Vehicle header */}
              <div>
                <h1 className="text-xl font-semibold text-white">
                  {[detail.vehicle?.year, detail.vehicle?.make, detail.vehicle?.model]
                    .filter(Boolean).join(' ') || 'Unknown Vehicle'}
                </h1>
                <div className="flex items-center gap-3 mt-1.5">
                  {detail.vehicle?.vin && (
                    <p className="text-xs font-mono" style={{ color: 'rgba(255,255,255,0.35)' }}>
                      VIN: {detail.vehicle.vin}
                    </p>
                  )}
                  {detail.created_at && (
                    <p className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>
                      {new Date(detail.created_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
              </div>

              {/* Summary */}
              {detail.summary && (
                <SectionCard title="Summary">
                  <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.65)' }}>
                    {detail.summary}
                  </p>
                </SectionCard>
              )}

              {/* Findings */}
              {detail.findings.length > 0 && (
                <SectionCard title="Inspection Findings">
                  <div className="space-y-3">
                    {detail.findings.map((f, i) => (
                      <FindingCard key={i} f={f} />
                    ))}
                  </div>
                </SectionCard>
              )}

              {/* Estimate */}
              {detail.estimate.length > 0 && (
                <SectionCard title="Estimate">
                  <div>
                    {/* Column headers */}
                    <div className="grid grid-cols-[1fr_60px_60px_72px] gap-2 pb-2 mb-2" style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
                      {['Service', 'Labor', 'Parts', 'Total'].map(h => (
                        <p key={h} className={`text-[10px] font-medium ${h !== 'Service' ? 'text-right' : ''}`} style={{ color: 'rgba(255,255,255,0.3)' }}>{h}</p>
                      ))}
                    </div>
                    {/* Rows */}
                    {detail.estimate.map((item, i) => {
                      const hourlyRate = item.labor_hours > 0 ? item.labor_cost / item.labor_hours : 0
                      return (
                        <div
                          key={i}
                          className="grid grid-cols-[1fr_60px_60px_72px] gap-2 py-2.5"
                          style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}
                        >
                          <div>
                            <p className="text-sm font-medium text-white">{item.part}</p>
                            {item.labor_hours > 0 && (
                              <p className="text-[10px] mt-0.5" style={{ color: 'rgba(255,255,255,0.3)' }}>
                                {item.labor_hours.toFixed(1)} hrs @ {formatCurrency(hourlyRate)}/hr
                              </p>
                            )}
                          </div>
                          <p className="text-xs text-right self-center" style={{ color: 'rgba(255,255,255,0.5)' }}>{formatCurrency(item.labor_cost)}</p>
                          <p className="text-xs text-right self-center" style={{ color: 'rgba(255,255,255,0.5)' }}>{formatCurrency(item.parts_cost)}</p>
                          <p className="text-sm font-semibold text-right self-center text-white">{formatCurrency(item.total)}</p>
                        </div>
                      )
                    })}
                    {/* Grand total */}
                    <div className="flex items-center justify-between pt-3">
                      <p className="text-sm font-semibold text-white">Grand Total</p>
                      <p className="text-lg font-bold" style={{ color: 'var(--accent)' }}>
                        ${detail.total.toFixed(2)}
                      </p>
                    </div>
                  </div>
                </SectionCard>
              )}

              {/* Actions */}
              <div className="flex gap-3 pt-1 pb-6">
                <button
                  onClick={() => navigator.clipboard.writeText(`${window.location.origin}/r/${detail.share_token}`)}
                  className="text-sm px-4 py-2 rounded-lg transition-colors"
                  style={{ border: '1px solid rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.6)', background: 'transparent' }}
                  onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)'}
                  onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = 'transparent'}
                >
                  📋 Copy Share Link
                </button>
                <a
                  href={`${API_URL}/reports/${detail.id}/pdf`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm px-4 py-2 rounded-lg transition-opacity text-white"
                  style={{ background: 'var(--accent)' }}
                >
                  🖨 Open Report PDF
                </a>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </AppShell>
  )
}

export default function ReportsPage() {
  return (
    <Suspense>
      <ReportsPageInner />
    </Suspense>
  )
}
```

- [ ] **Step 3: Test visual changes in browser**

Navigate to `http://localhost:3000/reports`. Select a report from the list. Verify:
- Selected report has accent-colored left border
- Section cards have glass backgrounds
- Findings show `✕` / `⚠` / `✓` icons with correct colors
- Estimate rows show labor sub-line (e.g. "1.5 hrs @ $85/hr")
- Grand total uses `var(--accent)` color
- PDF button uses `var(--accent)` background

- [ ] **Step 4: Test voice_select**

Navigate to `http://localhost:3000/reports?voice_select=civic`. The first report with "civic" in the vehicle name should auto-select.

- [ ] **Step 5: Commit**

```bash
git add web/app/reports/page.tsx
git commit -m "feat(reports): glass cards, severity icons, accent colors, voice_select param"
```

---

## Task 9: End-to-end voice test and deploy

- [ ] **Step 1: Full voice walkthrough**

With dev server running at `http://localhost:3000`:

1. Log in with `owner@shop.com` / `testpass`
2. Click the mic button in the nav bar — ring turns green (VAD active)
3. Say **"go to customers"** → should navigate to `/customers`
4. Say **"open John Smith"** (or any customer name) → customer should auto-select
5. Say **"go to chat"** → should navigate to `/chat`
6. Say **"select Tom"** → Tom should become the active agent in the sidebar
7. Say **"send a message: what's the labor cost for a brake job?"** → message should be sent to Tom
8. Say **"go to reports"** → should navigate to `/reports`
9. Say **"open the Civic report"** (or any vehicle) → report should auto-select
10. Click the PTT button → ring changes to amber PTT mode; hold mic button to speak

- [ ] **Step 2: Deploy to Vercel**

```bash
cd web
npx vercel --prod
```

Note the deployment URL from the output.

- [ ] **Step 3: Commit if any last-minute fixes were made**

```bash
git add -A
git commit -m "fix(voice): address any issues found during e2e test"
```

---

## Self-review notes (already applied)

- `voice_select` URL param approach avoids race condition where page isn't mounted when tool fires
- `useVoiceControl` options are memoized via `useMemo` — avoids infinite session sync loop
- VoiceContext uses `useRef` for callbacks (not state) — registrations don't trigger re-renders
- `report_id` chip detected from both history scan and live streaming events
- Labor hours sub-line guards `labor_hours > 0` to avoid division by zero
- No audio output from model (`outputMode: 'tool-only'`) — silent tool execution only
