# Web Parity Design

## Goal

Bring the Next.js web app to full iOS parity: customers, vehicles, upload-based inspection, complete report detail with per-finding photos, and all wrapped in a new top-nav + split-panel shell.

---

## Decisions

| Question | Decision |
|---|---|
| Navigation structure | Top nav + split panel (Option C) |
| Inspection recording | Upload-first: audio/video file + photo drag-and-drop; no live camera |
| Implementation approach | Layout-first rebuild: new shell first, then migrate chat/reports, then add new sections |
| Consumer report `/r/[token]` | Unchanged — no shell, no auth |

---

## Architecture

### Shell (`components/AppShell.tsx`)

New top-nav shell replaces the existing icon-rail + agent-sidebar shell.

**Top nav** (44px, `bg-gray-900`, `border-b`):
- Left: logo mark + "AutoShop" wordmark
- Center: nav links — Customers · Reports · Inspect · Chat — each with icon + label; active tab has `border-b-2 border-indigo-500 text-indigo-400`; inactive `text-gray-500`
- Right: user avatar (initials), clicking logs out

**Body** below nav: full viewport height minus nav. Each section renders its own two-panel split inside the body. The shell provides the nav and auth check only — panels are owned by each page.

**Auth**: same localStorage token check on mount → redirect to `/login` if missing. No change to auth logic.

### Routes

| Route | Shell | Description |
|---|---|---|
| `/` | — | Redirect to `/customers` |
| `/login` | — | Existing login page, unchanged |
| `/customers` | ✓ | Customer list (left) + vehicle cards (right) |
| `/reports` | ✓ | Report list (left) + report detail (right) |
| `/inspect` | ✓ | Vehicle picker (left) + upload panel (right) |
| `/chat` | ✓ | Agent picker (left) + chat panel (right) — existing ChatPanel migrated |
| `/r/[token]` | — | Public consumer report, unchanged |

Remove: `/dashboard` and `/dashboard/reports/[id]` (replaced by `/reports`).

---

## Sections

### 1. Customers (`/customers`)

**Left panel** (220px, fixed): Customer list with search bar and "+ Add" button.
- Each row: avatar (initials, color-hashed), name, vehicle count
- Selected row highlighted with `border-l-2 border-indigo-500`
- "+ Add" opens a modal: name (required), email, phone → `POST /customers`

**Right panel**: When a customer is selected, shows their detail.
- Header: avatar, name, email + phone, "Edit" button, "+ Add Vehicle" button
- Body: vehicle cards in a horizontal row
  - Each card: year/make/model, trim + color, report count, quote count
  - Clicking a vehicle navigates to `/reports?vehicleId={id}` (pre-filters reports list)
  - Dashed "+ Add vehicle" card at the end
- "+ Add Vehicle" / dashed card opens a modal: year (required), make (required), model (required), trim, VIN, color → `POST /customers/{id}/vehicles`

When no customer selected: empty state "Select a customer".

### 2. Reports (`/reports`)

**Left panel** (260px): All reports, newest first. Optional `?vehicleId=` query param pre-filters.
- Each row: vehicle year/make/model, report date, status badge, estimate total
- Search/filter bar at top

**Right panel**: Full report detail when a report is selected.
- Vehicle header: year/make/model + VIN
- Summary paragraph (if present)
- Findings section: each finding as a card — severity icon + color (red/orange/green), part name, notes. If `photo_url` present, full-width image below the text.
- Estimate table: service | labor | parts | total per row, grand total row
- "Share with Customer" button → copies `/r/{shareToken}` link to clipboard
- "Open Report PDF" link → `GET /reports/{id}/pdf` (public, opens in new tab)

### 3. Inspect (`/inspect`)

Upload-first inspection flow — no live camera, no microphone access.

**Left panel** (220px): Vehicle picker.
- Customer list collapsible sections; selecting a customer expands their vehicles
- Clicking a vehicle selects it and activates the right panel
- "Start Inspection" button enabled only when a vehicle is selected

**Right panel**: Upload panel (active after vehicle selected).

**Step 1 — Upload audio/video** (required):
- Drag-and-drop zone or "Browse files" button; accepts MP3, M4A, MP4, MOV, WAV
- On file select: `POST /transcribe` with audio blob → shows live transcript preview
- File name + duration shown after upload

**Step 2 — Upload inspection photos** (optional):
- Multi-file drop zone; accepts JPG, PNG, HEIC, WEBP; up to 20 files
- Each uploaded file: `POST /upload` → S3 URL returned; thumbnail grid shown
- Photos can be removed before analysis

**Step 3 — Analyze** button (enabled once audio uploaded):
1. `POST /sessions` with `vehicle_id`, `pricing_flag: "shop"` → session ID
2. Upload audio file: `POST /sessions/{id}/media` (multipart, tag: `general`) — backend transcribes during finalize
3. For each photo: `POST /sessions/{id}/media` (multipart, tag: `general`)
4. `POST /sessions/{id}/finalize` → returns findings, estimate, quote ID
5. On success: navigate to `/reports` with the new report pre-selected

The `/transcribe` endpoint is used only for the transcript preview in Step 1 (UX feedback) — not part of the session submission.

Loading state during steps 1-4 with progress indicator.

### 4. Chat (`/chat`)

**Left panel** (180px): Agent list — "Assistant" and "Tom" (same as current `AgentList.tsx`).

**Right panel**: Existing `ChatPanel.tsx` — no functional changes. `QuoteSummary` sidebar continues to appear inside the chat panel as it does today.

The only change is removing `AppShell.tsx`'s old icon rail wrapper; `ChatPanel` is placed directly in the right-panel slot.

---

## New API Functions (`lib/api.ts`)

```typescript
getCustomers(): Promise<Customer[]>
createCustomer(data: { name, email?, phone? }): Promise<Customer>
getVehicles(customerId: string): Promise<Vehicle[]>
createVehicle(customerId: string, data: { year, make, model, trim?, vin?, color? }): Promise<Vehicle>
getAllReports(vehicleId?: string): Promise<ReportSummary[]>
getReport(id: string): Promise<ReportDetail>
createSession(vehicleId: string): Promise<{ session_id: string }>
uploadMedia(sessionId: string, file: File, tag: string): Promise<{ url: string }>
finalizeSession(sessionId: string): Promise<FinalizeResult>
```

Types mirror `APIModels.swift` (snake_case in API, camelCase in TS).

---

## Files Changed or Created

| File | Action | Notes |
|---|---|---|
| `components/AppShell.tsx` | Rewrite | Top nav + auth check; panels owned by pages |
| `components/AgentList.tsx` | Keep | Moved into `/chat` page's left panel |
| `app/page.tsx` | Edit | Redirect to `/customers` instead of `/chat` |
| `app/customers/page.tsx` | Create | Customer list + vehicle detail |
| `app/reports/page.tsx` | Create | Report list + full detail |
| `app/inspect/page.tsx` | Create | Upload inspection flow |
| `app/chat/page.tsx` | Edit | Wrap ChatPanel in new two-panel layout |
| `app/dashboard/page.tsx` | Delete | Replaced by `/reports` |
| `app/dashboard/reports/[id]/page.tsx` | Delete | Replaced by `/reports` |
| `lib/api.ts` | Edit | Add customer, vehicle, session, report API calls |
| `lib/types.ts` | Create | Shared TypeScript types (Customer, Vehicle, ReportDetail, etc.) |

---

## Out of Scope

- Mobile/responsive layout (desktop-first; don't break it, but don't optimize)
- Push notifications
- Offline support
- Quote editing on web (view-only via chat or report PDF)
