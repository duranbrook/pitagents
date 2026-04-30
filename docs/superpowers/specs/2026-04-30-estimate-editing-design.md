# Estimate Editing Design

**Date:** 2026-04-30  
**Status:** Approved

## Goal

Add inline estimate editing to the web report page — separate Hours and $/hr columns, auto-save on blur, voice commands to edit lines and add new service lines, and a "Regenerate PDF" button. The same editing functionality lands on iOS and Android in separate workstreams.

---

## Architecture

Three workstreams, one shared backend endpoint:

- **Backend + Web** (`feat/estimate-editing`) — New `PATCH /reports/{id}/estimate` endpoint; web `EstimateTable` component; two new voice tools via VoiceContext; PDF regeneration button.
- **iOS** (`feat/estimate-editing-ios`) — Tap-to-edit sheet in `ReportDetailView`; PDF via `SafariViewController`.
- **Android** (`feat/estimate-editing-android`) — Tap-to-edit dialog in `ReportDetailScreen`; PDF via `CustomTabsIntent`.

All three workstreams can run in parallel once the backend endpoint is deployed to Railway.

---

## Data Model

### Current estimate item schema (JSON stored in `reports.estimate`)

```json
{
  "part": "Brake pad replacement",
  "labor_hours": 2.0,
  "labor_cost": 250.00,
  "parts_cost": 85.00,
  "total": 335.00
}
```

### Updated schema (adds `labor_rate`)

```json
{
  "part": "Brake pad replacement",
  "labor_hours": 2.0,
  "labor_rate": 125.0,
  "labor_cost": 250.00,
  "parts_cost": 85.00,
  "total": 335.00
}
```

`labor_rate` is optional for backward compatibility — old reports without it display a blank $/hr cell but remain readable.

### Derived fields (always backend-computed, never sent by clients)

- `labor_cost = labor_hours × labor_rate`
- `total = labor_cost + parts_cost`
- `estimate_total = Σ total across all items` (stored in `reports.estimate_total`)

---

## Backend

### New endpoint: `PATCH /reports/{id}/estimate`

**Auth:** `require_owner` (same as other mutating report endpoints)

**Request body:**
```json
{
  "items": [
    {
      "part": "Brake pad replacement",
      "labor_hours": 2.0,
      "labor_rate": 125.0,
      "parts_cost": 85.00
    }
  ]
}
```

**Behavior:**
1. Fetch report or 404
2. For each item: derive `labor_cost = labor_hours × labor_rate`, `total = labor_cost + parts_cost`
3. Compute new `estimate_total = Σ total`
4. Save `report.estimate = derived_items`, `report.estimate_total = estimate_total`
5. Return full staff-detail report object (same shape as `GET /reports/{id}`)

**File:** `backend/src/api/reports.py` — append PATCH handler after existing GET handlers

---

## Web — Estimate Table

### Column layout

```
Service          | Hours  | $/hr   | Parts    | Total
─────────────────┼────────┼────────┼──────────┼──────────
Brake pad repl.  | [2.0]  | [125]  | [$85.00] | $335.00
Oil change       | [0.5]  | [90]   | [$22.00] |  $67.00
─────────────────┴────────┴────────┴──────────┼──────────
                                               | $402.00
                                 [+ Add line]  | [Regenerate PDF]
```

- `Service` and `Total` cells are read-only
- `Hours`, `$/hr`, `Parts` cells are clickable — click turns the value into a `<input type="number">`
- `Total` per row recalculates live on input (client-side preview only)
- On blur: fire `PATCH /reports/{id}/estimate` with all current items; replace local state with response
- If PATCH fails: revert the edited cell to its pre-edit value; show one-line error below table

### Add service line

- "+ Add line" button appends a blank editable row
- New row does NOT fire PATCH on each individual field blur
- PATCH fires when all three fields (Hours, $/hr, Parts) have been filled and the last one blurs — or when the user presses Enter in any field
- Service name is a text input (not number)

### Regenerate PDF button

- Calls `GET /reports/{id}/pdf` — existing endpoint, streams PDF bytes
- Button shows a spinner while the fetch is in flight
- On success: open the blob URL in a new tab (`window.open(blobUrl, '_blank')`)
- On failure: show inline error "PDF generation failed"

### Files

- `web/app/reports/page.tsx` — add `EstimateTable` component (inline, same file is fine given current size), voice tool registration, PDF button
- `web/lib/api.ts` — add `patchReportEstimate(reportId, items)` function
- `web/lib/voice/tools.ts` — add `edit_estimate_line` and `add_estimate_line` tools
- `web/contexts/VoiceContext.tsx` — add `registerEditLine` and `registerAddLine` slots

---

## Voice Tools

Both tools are registered by the reports page on mount via new VoiceContext callbacks. Callbacks are cleaned up on unmount (set to null).

### `edit_estimate_line`

```
Description: Edit a field on an existing estimate line item.
Arguments:
  service (string) — partial name match, case-insensitive
  field   ("hours" | "rate" | "parts")
  value   (number)
```

Behavior: Find the first line whose `part` contains `service` (case-insensitive). Update the matching field. Fire PATCH with all current items.

### `add_estimate_line`

```
Description: Add a new service line to the estimate.
Arguments:
  service (string) — service name
  hours   (number)
  rate    (number)
  parts   (number)
```

Behavior: Append new item to local state. Fire PATCH with all items including the new one.

### VoiceContext additions

```ts
registerEditLine: (fn: (service: string, field: string, value: number) => void) => void
registerAddLine:  (fn: (service: string, hours: number, rate: number, parts: number) => void) => void
editLine: (service: string, field: string, value: number) => void
addLine:  (service: string, hours: number, rate: number, parts: number) => void
```

---

## iOS

**File:** `ios/AutoShop/Views/ReportDetailView.swift`  
- Estimate rows become tappable; tap opens a `.sheet` with three `TextField` controls (Hours, Rate, Parts) and a "Save" button
- On Save: call `PATCH /reports/{id}/estimate`, dismiss sheet, refresh report

**File:** `ios/AutoShop/Models/Report.swift` (or equivalent)  
- `EstimateItem` gains `laborRate: Double?` (optional, `CodingKeys` maps `"labor_rate"`)

**File:** `ios/AutoShop/Network/APIClient.swift`  
- Add `patchEstimate(reportId:, items:)` method returning `Report`

**PDF:** "Regenerate PDF" button opens `GET /reports/{id}/pdf` URL in `SFSafariViewController`

No voice control in this workstream — OpenAI Realtime is not on iOS yet.

---

## Android

**File:** `android/app/src/main/java/com/autoshop/ui/customers/ReportDetailScreen.kt`  
- Estimate rows become clickable; click opens an `AlertDialog` with three number fields (Hours, Rate, Parts) and OK/Cancel
- On OK: call PATCH endpoint via Retrofit, update local `StateFlow`

**File:** `android/app/src/main/java/com/autoshop/data/model/ApiModels.kt`  
- `EstimateItem` data class gains `val labor_rate: Double? = null`

**File:** `android/app/src/main/java/com/autoshop/data/network/MessagesApi.kt`  
- Add `@PATCH("reports/{id}/estimate")` suspend fun

**PDF:** "Regenerate PDF" button opens `GET /reports/{id}/pdf` URL via `CustomTabsIntent`

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| PATCH returns 4xx/5xx | Revert cell; show inline error |
| PDF fetch fails | Show inline "PDF generation failed" message |
| Voice: no matching line | Tool returns `{ success: false, message: "No line matching '…'" }` — model reads this and asks the user to clarify |
| Voice: ambiguous match (multiple lines match) | Return first match; model confirms in text what it changed |
| New line: partial blur (not all fields filled) | No PATCH fired; unsaved row styled with a dashed border |

---

## Out of Scope

- Deleting individual estimate lines (not requested)
- Reordering lines (not requested)
- Voice control on iOS or Android (OpenAI Realtime not on mobile yet)
- Automatic PDF regeneration on every save (user-triggered only)
