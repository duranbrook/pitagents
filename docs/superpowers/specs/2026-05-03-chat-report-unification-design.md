# Chat Report Unification Design

## Problem

The chat agent currently creates a `Quote` when asked to build an estimate. Quotes are a parallel model that never appear in Customers → Vehicle → Reports. The user sees a disconnected "Auto-Quote" card in chat, backed by `QuoteDetailView`, with no relationship to the inspection report the shop already uses.

The root cause: `Report.session_id` is `NOT NULL`, so the agent can't create a Report without a prior inspection session. The Quote was a workaround. It is now a source of confusion and duplication.

## Goal

A single unified flow: the chat agent creates a `Report` (same model as the inspection report). It appears in Customers → Vehicle → Reports alongside inspection-generated reports. Tapping the chat card opens `ReportDetailView` — the same page the shop already uses to edit estimates and regenerate PDFs.

## Design

### 1. Data Model

**Migration:** Make `Report.session_id` nullable (`NOT NULL` → nullable).

- Reports with `session_id` set = came from an inspection session (existing behavior, unchanged)
- Reports with `session_id = NULL` and `vehicle_id` set = created by chat agent (new)
- `vehicle_id` is always required for chat-created reports (ensures they appear on the vehicle page)

The `Quote` model is left in place but no longer created by any agent flow. Existing quotes stay in the DB dormant.

### 2. New Agent Tools (report_tools.py)

Replaces `quote_tools.py` in the agent tool registry.

**`search_vehicles(query: str)`**  
Full-text search across vehicles (year, make, model) and their linked customer names. Returns a list of `{vehicle_id, label, customer_name}`. The agent uses this to resolve "James Carter's Camry" → a real `vehicle_id`.

**`create_report(vehicle_id: str)`**  
Creates a new `Report` row with `session_id=NULL`, `vehicle_id=vehicle_id`, `status="draft"`. Returns `{report_id}`.

**`add_report_item(report_id: str, part: str, labor_hours: float, labor_rate: float, parts_cost: float)`**  
Appends one item to `report.estimate` (the existing JSONB field). Item shape matches what `ReportDetailView` already renders:
```json
{ "part": "...", "laborHours": 1.5, "laborRate": 120.0, "partsCost": 89.99 }
```
Returns updated estimate list and total.

**`list_report_items(report_id: str)`**  
Returns current estimate items and total. Agent uses this to summarise before embedding the link.

No finalize tool — the user does that in-app by tapping "Regenerate Report PDF."

### 3. Agent System Prompt

- Remove `QUOTE_BUILD` / `QUOTE_REVIEW` prompt blocks
- Add `REPORT_BUILD` block instructing the agent to: call `search_vehicles` first, then `create_report`, then `add_report_item` per line item, then embed `[REPORT:<uuid>]` in its final message
- Intent label `QUOTE_BUILD` → `REPORT_BUILD`

### 4. Backend API

`GET /reports/{report_id}` already exists and returns the full report. One change: the response must not fail when `session_id` is NULL. Audit the endpoint to confirm it doesn't call `select(InspectionSession).where(...)` unconditionally.

`PATCH /reports/{report_id}/estimate` already exists — used by `ReportDetailView` to edit items. No changes needed.

`GET /reports/{report_id}/pdf` already exists — used by "Regenerate Report PDF." Audit for NULL `session_id` safety (the PDF generator may try to load session media).

New endpoint needed: **`GET /vehicles/{vehicle_id}/search`** (or reuse existing customer/vehicle endpoints) for the `search_vehicles` tool.

### 5. iOS

**`ChatHistoryItem` extension:**  
Parse `[REPORT:<uuid>]` instead of `[QUOTE:<uuid>]`. Rename computed property `quoteId` → `reportId`. Update `displayTextClean` regex accordingly.

**`ReportCardBubble`:**  
- Remove `QuoteResponse` state and `fetchQuote` call
- Load report directly via `APIClient.shared.getReport(reportId:)`  
- Card shows "Inspection Report" label always (no status pill distinction needed)
- Opens `ReportDetailView(reportId:, vehicleLabel:, presentedFromChat: true)` directly

**`VehicleDetailView`:**  
No changes — it already lists all `Report` rows for a vehicle via `GET /vehicles/{id}/reports`. Chat-created reports appear automatically.

**`AssistantView`:**  
Update `if msg.role != "user", let qid = msg.quoteId` → use `msg.reportId`.

### 6. What Is Not Changing

- Technician inspection flow (Session → Report) — untouched
- `ReportDetailView` — untouched (it already handles the edit + PDF flow)
- `VehicleDetailView` reports list — untouched
- Existing `Quote` rows in DB — left dormant, no migration needed
- `QuoteDetailView` — can stay in the codebase for now (no existing entry points once `ReportCardBubble` is updated)

## Error Handling

- `search_vehicles` returns empty list → agent tells user it couldn't find the vehicle, asks for more detail
- `create_report` with invalid `vehicle_id` → 404, agent surfaces error
- PDF generation with `session_id=NULL` — no inspection media, PDF contains estimate only (no photos)

## Testing Criteria

- Ask a chat agent "build a repair estimate for brake pads on [known vehicle]" → report card appears in chat
- Tap card → `ReportDetailView` opens with correct line items
- Navigate to Customers → that vehicle → Reports → same report appears in the list
- Edit an estimate item in `ReportDetailView` → total updates
- Tap "Regenerate Report PDF" → PDF generates successfully
- Existing inspection reports (session-linked) still work and still appear in the vehicle page
