# iOS Technician Chat — Design Spec
**Date:** 2026-05-02  
**Status:** Approved

---

## Overview

Replace the Inspect tab with a role-aware chat experience for technicians. A technician logs in and lands directly in a one-on-one AI chat that guides them through capturing vehicle information, describing issues, and generating a finalized repair quote — all without leaving the chat window.

---

## 1. Role-Based Navigation

`MainTabView` branches on `appState.userRole` (already decoded from JWT):

| Role | Tabs |
|---|---|
| `owner` | Customers · Assistant (agent list) · Profile |
| `technician` | Customers · Chat · Profile |

The **Inspect** tab is removed for all roles — it was testing scaffolding.

The technician **Chat** tab mounts `AgentChatView` directly with the tech agent ID pre-loaded (fetched from the `/agents` list on login; the technician's shop has exactly one agent). No agent-picker list is shown.

---

## 2. iOS Component Changes

### 2a. `MainTabView.swift`
Switch on `appState.userRole`. Technician branch bypasses `AssistantView` and mounts `AgentChatView(agent:techAgent, showMediaControls: true)`.

### 2b. `AgentChatView.swift`
Add a `showMediaControls: Bool` parameter (default `false`). When `true`:
- The input bar is replaced by `TechnicianInputBar`
- The nav bar shows a collapse/expand **⌃** button (top-right)
- The chat history area shrinks to a peek strip when input is expanded

### 2c. New `TechnicianInputBar.swift`
Handles all media input state and renders the input area in two modes.

**Compact mode** (default):
```
[📷] [🎬] [🎙]  [ Message…          ] [↑]
```

**Expanded mode** (triggered by: transcription arriving, user typing, photo/video attached):
```
┌──────────────────────────────────────────┐
│ 🎙 Transcribed — edit freely, then send  │
│ ┌────────────────────────────────────┐   │
│ │ <large scrollable editable textarea>│  │
│ └────────────────────────────────────┘   │
│ [VIN🟠] [photo] [+]                      │
│ [📷] [🎬] [🎙]     [    Send ↑        ]  │
└──────────────────────────────────────────┘
```

**Collapse behaviour:**
- Auto-expands when content arrives
- Manual collapse: tap **⌃** button in nav bar
- Auto-collapses when agent replies

---

## 3. Media Input Detail

### 3a. Camera (📷) — long-press → action sheet
Long-pressing the camera button presents an action sheet:
- **Take Photo** — opens standard camera
- **Scan VIN** — opens camera with a horizontal rectangle viewfinder overlay optimised for VIN plates; captured photo is auto-tagged as VIN in the tray
- **Choose from Library**

Multiple shots can be taken in sequence. After returning from camera, a **photo tray** appears above the input row showing thumbnails. Each photo is:
- Tappable to toggle selected/deselected (blue ✓ badge)
- Long-pressable for a context menu: *Mark as VIN / Select / Remove*
- Tagged with an orange **VIN** badge if captured via Scan VIN (or manually marked)

Only selected photos are sent. The ➕ thumbnail opens camera again for more shots.

### 3b. Video (🎬)
Opens the camera in video mode with audio recording enabled. On stop:
1. Raw video (with audio) is uploaded to S3 via `POST /upload/video`
2. Backend returns `{ video_url }` — stored stably (not presigned) and attached to the report for customer viewing
3. A video thumbnail appears in the tray, labelled **VIDEO**

No frame extraction in this phase.

### 3c. Voice (🎙) — two modes, configurable in Settings
| Mode | Behaviour |
|---|---|
| **Hold** | Hold button → record → release → auto-transcribe |
| **Auto-detect** | Tap to start → silence detection stops recording → auto-transcribe |

In both modes:
- Audio is POSTed to `POST /transcribe`
- Transcribed text drops into the editable textarea (yellow tint, hint label above)
- Camera/video buttons dim while recording

---

## 4. Agent Reply — Report Card Bubble

When the agent finalises a quote, it replies with a structured **report card** bubble:

```
┌──────────────────────────────┐
│ 🔵 Inspection Report          │
│    Sarah Chen                 │
│    2019 Honda Civic · VIN…   │
├──────────────────────────────┤
│ Front brake pads ×2  $179.98 │
│ Front left rotor     $129.99 │
│ Labor (2.5 hrs)      $300.00 │
├──────────────────────────────┤
│ Total                $609.97 │
├──────────────────────────────┤
│ 🔗  View full report →        │
└──────────────────────────────┘
```

The **View full report** link opens the report's web URL in `SFSafariViewController` (in-app browser).

---

## 5. Backend Changes

### 5a. `Quote` model — new column
Add `vehicle_id: UUID FK → vehicles.id (nullable)`.  
One Alembic migration.

### 5b. `create_quote` tool — updated signature
```python
create_quote(vehicle_id: str | None = None, session_id: str | None = None)
```
Sets `vehicle_id` on the new quote row.

### 5c. New tool: `find_vehicle_by_vin(vin: str)`
Added to `vin_tools.py`. Queries `vehicles` table by VIN (case-insensitive).  
Returns `{ vehicle_id, customer_id, year, make, model, customer_name }` or `{ error }`.

### 5d. `finalize_quote` — auto-creates Report
When `vehicle_id` is set, `finalize_quote` creates a `Report` record linked to the vehicle with the quote's line items as the estimate. No separate agent tool call needed.

### 5e. `MessageRequest` — multi-image
```python
# Before
image_url: str | None = None

# After
image_urls: list[str] = []
```
`_build_user_content` loops over `image_urls`. Backward-compatible.

### 5f. New endpoint: `POST /upload/video`
Accepts multipart video file. Stores to S3. Returns `{ video_url }`.

### 5g. Tech agent tool set (configured in DB)
`find_vehicle_by_vin` · `lookup_part_price` · `estimate_labor` · `create_quote` · `create_quote_item` · `finalize_quote`

---

## 6. End-to-End Flow

```
1. Login → role = technician → Chat tab → tech agent conversation opens

2. Agent: "Hi! Scan the VIN plate to identify the vehicle."

3. Technician long-presses 📷 → Scan VIN → camera with viewfinder → photo captured
   → VIN photo appears in tray with orange badge

4. Technician adds damage photos via Take Photo, records video via 🎬,
   describes issues via 🎙 voice (transcribed into editable textarea)

5. Technician hits Send ↑ → all selected photos + transcribed text sent to agent

6. Agent calls find_vehicle_by_vin(vin) → resolves vehicle + customer
   If VIN not found → agent asks follow-up: "Which customer is this for?"

7. Agent calls create_quote(vehicle_id) → adds line items via create_quote_item
   → calls finalize_quote → Report auto-created and linked to vehicle

8. Agent replies with report card bubble + "View full report →" link

9. Input collapses back to compact. Technician can continue for the next vehicle.
```

---

## 7. Out of Scope (this phase)

- Video frame extraction / LLM vision analysis of video
- Cross-platform report retrieval (web + iOS) beyond the existing web dashboard
- Owner-role UI changes beyond removing the Inspect tab
- Push notifications when report is ready
