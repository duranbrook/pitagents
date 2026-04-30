# Voice Layer + Report Preview Design

**Date:** 2026-04-30  
**Sub-projects:** A (Voice layer) + B (Report preview polish)

---

## Goals

- **A — Voice layer:** Let the shop owner control the web app by speaking. Navigate tabs, select agents, send chat messages, open customer records, open reports — all hands-free.
- **B — Report preview:** Bring the web Reports page to visual parity with the iOS `ReportDetailView`. Glass-card sections, severity icons, labor-hours breakdown, accent-color theming, deep-link from chat.

---

## Architecture

### Sub-project A: Voice Layer

**Session route — `/api/session`**  
A Next.js Route Handler (server component, never bundled into the browser). Reads `process.env.OPENAI_API_KEY`, POST to `https://api.openai.com/v1/realtime/sessions` with model `gpt-4o-mini-realtime-preview`, returns the `client_secret.value` as `{ token }`. The API key never reaches the client.

**`VoiceContext`**  
A React context placed in `providers.tsx` above everything else. Holds three mutable callback refs:

```ts
type VoiceContextValue = {
  registerNavigate: (fn: (tab: string) => void) => void
  registerSelectAgent: (fn: (name: string) => boolean) => void
  registerSendMessage: (fn: (text: string) => void) => void
  registerSelectCustomer: (fn: (name: string) => boolean) => void
  registerSelectReport: (fn: (query: string) => boolean) => void
  // dispatchers (called by voice tools)
  navigateTo: (tab: string) => void
  selectAgent: (name: string) => boolean
  sendMessage: (text: string) => void
  selectCustomer: (name: string) => boolean
  selectReport: (query: string) => boolean
}
```

`AppShell` calls `registerNavigate` on mount. `ChatPanel` calls `registerSelectAgent` and `registerSendMessage` on mount. `CustomersPage` calls `registerSelectCustomer`. `ReportsPage` calls `registerSelectReport`.

**Voice tools (5 total)**  
All defined with `defineVoiceTool()` (Zod schema). The `execute()` function calls the corresponding dispatcher from `VoiceContext`.

| Tool | Args | Description |
|---|---|---|
| `navigate_to_tab` | `tab: 'customers'\|'reports'\|'inspect'\|'chat'` | Push to matching route |
| `select_agent` | `name: string` | Case-insensitive `includes()` match on agent display name |
| `send_message` | `text: string` | Inject into chat input and submit |
| `select_customer` | `name: string` | Navigate to Customers; select first customer whose name includes the query (case-insensitive) |
| `select_report` | `query: string` | Navigate to Reports; select first report whose vehicle label includes the query (case-insensitive) |

**`VoiceControlWidget`**  
A small component rendered in `AppShell` nav, right of the existing nav items, left of the user avatar button.

- Mic icon button — click connects/disconnects the WebRTC session
- Status ring: gray = idle, pulsing green = listening (VAD), amber = processing, red = error
- A tiny `PTT` toggle pill overlaid on the button when connected — switches between `vad` and `push-to-talk` activation modes
- On `push-to-talk` mode: button becomes hold-to-speak (mousedown/touchstart = startCapture, mouseup/touchend = stopCapture)

**Voice pipeline:**
1. User clicks mic → fetch `/api/session` → get ephemeral token → connect WebRTC via `createVoiceControlController` from the reference library (code copied into `web/lib/voice/`)
2. OpenAI VAD detects utterance → streams to model
3. Model emits function call → `execute()` dispatches VoiceContext callback → UI updates
4. `outputMode: 'tool-only'` — no audio back from the model, silent tool execution only

**Activation mode config:**
- Default: `activationMode: 'vad'`
- Toggle state held in `VoiceControlWidget` local state, passed to controller via `configure()`

**Library approach:**  
Copy the relevant source files from `/Users/joehe/workspace/learning/realtime-voice-component/src/` into `web/lib/voice/` rather than installing as a package. Files needed:
- `voiceControlController.ts`
- `useVoiceControl.ts`
- `defineVoiceTool.ts`
- `schema.ts`
- `types.ts`
- `transport/webRtcRealtimeTransport.ts`
- `transport/types.ts`

This avoids npm registry dependency. Run `npm install zod` — it is not currently in `web/package.json`.

---

### Sub-project B: Report Preview Polish

**File:** `web/app/reports/page.tsx` (modify in place, no new route needed)

**Visual changes:**

1. **Section cards:** Wrap each section (Vehicle, Summary, Findings, Estimate) in a card: `background: rgba(255,255,255,0.03)`, `border: 1px solid rgba(255,255,255,0.07)`, `border-radius: 12px`, padding `16px`. Matches the glass aesthetic used in the rest of the app.

2. **Accent color:** Replace all `indigo-400/500/600` with `var(--accent)`. Applies to: grand total text, report list active border, PDF button background, "copy share link" button text.

3. **Severity icons in `FindingCard`:**
   - `high` / `urgent` → red `✕` icon + `text-red-400` badge
   - `medium` / `moderate` → amber `⚠` icon + `text-amber-400` badge
   - `low` / other → green `✓` icon + `text-green-400` badge

4. **Estimate row sub-line:** Below each service name, render `{labor_hours.toFixed(1)} hrs @ ${(labor_cost / Math.max(labor_hours, 0.1)).toFixed(0)}/hr` in `text-xs text-gray-500`.

5. **Report list active state:** Replace `border-indigo-500 bg-gray-700` with `border-[var(--accent)] bg-white/5`.

**Deep-link from chat:**  
In `ChatPanel.tsx` (or `MessageBubble.tsx`), detect when a tool call output contains a `report_id` field. When found, render a `"View Report →"` chip below the message that links to `/reports?id={report_id}`. The reports page already handles `?id=` via `searchParams`.

Detection: scan `toolCalls` in the message for any call where `output?.report_id` exists (string). The backend already returns `report_id` in quote finalization tool responses.

---

## Data Flow

```
Voice utterance
  → OpenAI Realtime (VAD + STT + LLM)
  → function_call event (DataChannel)
  → VoiceControlController.execute()
  → VoiceContext dispatcher
  → React state update / router.push
  → UI reflects change
  → tool result sent back to model
  → model acknowledges (no audio output)
```

---

## Error Handling

- **Mic permission denied:** `VoiceControlWidget` shows red status, tooltip "Microphone access required"
- **Session fetch fails:** Same red state, tooltip "Could not connect voice session"
- **Tool `select_agent` with no match:** Returns `{ ok: false, message: "No agent found matching '{name}'" }` to model; model voices clarification
- **Tool `select_customer/report` with no match:** Same pattern — return error to model, model asks for clarification
- **WebRTC disconnect:** Auto-resets to idle state; user must click again to reconnect (no auto-reconnect)

---

## File Map

| Action | File |
|---|---|
| Create | `web/app/api/session/route.ts` |
| Create | `web/lib/voice/voiceControlController.ts` (copied + typed) |
| Create | `web/lib/voice/useVoiceControl.ts` |
| Create | `web/lib/voice/defineVoiceTool.ts` |
| Create | `web/lib/voice/schema.ts` |
| Create | `web/lib/voice/types.ts` |
| Create | `web/lib/voice/transport/webRtcRealtimeTransport.ts` |
| Create | `web/lib/voice/transport/types.ts` |
| Create | `web/lib/voice/tools.ts` (the 5 tool definitions) |
| Create | `web/contexts/VoiceContext.tsx` |
| Create | `web/components/VoiceControlWidget.tsx` |
| Modify | `web/app/providers.tsx` (add VoiceContext) |
| Modify | `web/components/AppShell.tsx` (add VoiceControlWidget, registerNavigate) |
| Modify | `web/components/chat/ChatPanel.tsx` (registerSelectAgent, registerSendMessage, report chip) |
| Modify | `web/app/customers/page.tsx` (registerSelectCustomer) |
| Modify | `web/app/reports/page.tsx` (registerSelectReport + all visual polish) |

---

## Testing Checklist

- [ ] `/api/session` returns a token (curl test)
- [ ] Mic button connects; status ring animates green in VAD mode
- [ ] Saying "go to reports" navigates to `/reports`
- [ ] Saying "select Tom" switches active agent in chat sidebar
- [ ] Saying "tell the assistant the brakes are squeaking" sends that message
- [ ] Saying "open John Smith" selects that customer
- [ ] Saying "open the Civic report" opens the correct report
- [ ] PTT toggle works: hold-to-speak, release-to-send
- [ ] Report card sections use glass styling
- [ ] Grand total uses `var(--accent)`
- [ ] Severity icons render correctly
- [ ] Labor hours sub-line appears in estimate rows
- [ ] "View Report →" chip appears in chat after report generation
- [ ] Deep-link `/reports?id=X` opens correct report pre-selected
