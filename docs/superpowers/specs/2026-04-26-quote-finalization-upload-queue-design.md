# Design Spec: Quote Finalization + Media Upload Queue

**Date:** 2026-04-26  
**Status:** Approved  
**Scope:** iOS app + FastAPI backend

---

## Overview

Two features that complete the inspection-to-quote workflow:

1. **Media upload queue** — photos and videos appear in the thumbnail strip immediately from local storage; a background URLSession uploads them concurrently while the technician keeps working.
2. **Quote finalization + PDF generation** — tapping "Finalize Quote" produces two PDFs (Estimate + Inspection Report), stores them in S3, links the report to the vehicle so it appears in the customer-facing Reports tab.

---

## Feature 1: Media Upload Queue (URLSession Background)

### Motivation

Currently, thumbnails only appear after a successful upload. If the network is slow, the technician sees nothing and doesn't know if the photo was captured. The new design shows thumbnails instantly from the local file and uploads in the background.

### Upload Item Lifecycle

```
captured → pending → uploading → done
                              ↘ failed → (tap to retry)
```

- **captured**: file saved to `Documents/Uploads/{sessionId}/{uuid}.{ext}` immediately on capture. Moving to `Documents/` (away from the temp directory) is required for URLSession background uploads — iOS needs a persistent file path.
- **pending**: item added to `UploadManager.queue`; upload task not yet started.
- **uploading**: background URLSession task is active; progress shown on badge.
- **done**: server returned 2xx; `s3_url` stored on the item; local file deleted.
- **failed**: 3 automatic retries with exponential backoff (1s, 2s, 4s). After all retries exhausted, badge shows ↺ — tap to retry manually.

### iOS Components

#### `UploadItem`
```swift
struct UploadItem: Identifiable {
    let id: UUID
    let localURL: URL          // Documents/Uploads/…
    let type: String           // "photo" | "video" | "audio"
    let tag: String            // always "general" for now
    var status: UploadStatus   // .pending | .uploading(progress) | .done | .failed(Error)
    var s3URL: String?
}

enum UploadStatus {
    case pending
    case uploading(Double)     // 0.0 – 1.0
    case done
    case failed(Error)
}
```

#### `UploadManager` (singleton)
- Owns a `URLSession(configuration: .background(withIdentifier: "com.autoshop.uploads"))`.
- Implements `URLSessionTaskDelegate` and `URLSessionDataDelegate` for progress and completion.
- Exposes `@Published var items: [UploadItem]` observed by `RecordingView`.
- `func enqueue(_ item: UploadItem, sessionId: String)` — starts the background upload task.
- `func retry(id: UUID)` — resets status to `.pending` and re-enqueues.
- `func remove(id: UUID)` — cancels any in-flight task, deletes local file, removes from array.
- On app relaunch, `URLSession` delegate callbacks are re-attached automatically by iOS for any in-flight tasks (standard background URLSession behaviour).

#### `RecordingView` changes
- Removes `capturedMedia: [CapturedMediaItem]` array.
- Observes `UploadManager.shared.items` filtered to the current `sessionId`.
- On photo/video capture: moves file to `Documents/Uploads/`, calls `UploadManager.shared.enqueue(...)`.
- "Generate Quote" button disabled if any item is `.pending` or `.uploading`. Enabled when all items are `.done` (failed items must be retried or removed first).

#### `MediaThumb` changes
- Reads image from `item.localURL` immediately (no waiting for upload).
- Badge overlaid on thumbnail corner:
  - `.pending` → grey `…`
  - `.uploading(progress)` → yellow `↑` with circular progress ring
  - `.done` → green `✓`
  - `.failed` → red `↺` (tap triggers `UploadManager.shared.retry(id:)`)
- Long-press → context menu: **Remove** (calls `UploadManager.shared.remove(id:)`).

### Backend

No backend changes required. The existing `POST /sessions/{session_id}/media` multipart endpoint already handles each file upload independently.

---

## Feature 2: Quote Finalization + PDF Generation

### Motivation

Quotes currently stay in `draft` status forever. Finalizing should produce two printable PDFs stored in S3 and link the resulting report to the correct vehicle so it surfaces in the iOS Customers → Vehicle → Reports tab.

### Two Output Documents

| Document | Audience | Content | Stored on |
|---|---|---|---|
| **Estimate PDF** | Customer signs this | Shop header, customer/vehicle info, line items (labor vs parts), subtotals, tax, total, signature line | `quotes.pdf_url` |
| **Inspection Report PDF** | Customer keeps a copy | Shop header, vehicle banner, AI summary, findings table (Service Now / Monitor / Good badges), photo grid, estimate summary, share link | `reports.pdf_url` |

### Finalize Flow (step by step)

1. **iOS** — user taps "Finalize Quote" in `QuoteDetailView`. Button disabled, spinner shown. Calls `PUT /quotes/{quote_id}/finalize`.

2. **Backend** — loads `Quote` → follows `quote.session_id` → loads `InspectionSession`.

3. **Backend** — extracts `vehicle_id` from `session.vehicle["vehicle_id"]` (UUID string stored in the JSON snapshot at session creation). This is the FK that links the Report to the vehicle row.

4. **Backend** — if a `Report` row already exists for `session_id`, update it in place; otherwise create a new one:
   - `session_id` = session.id
   - `vehicle_id` = UUID parsed from `session.vehicle["vehicle_id"]`. If the field is absent (session started without selecting a vehicle — not possible in the current iOS flow but guard anyway), set `vehicle_id = None` and skip the vehicle-linked Reports tab; the report will still be generated and accessible via the share token.
   - `findings`, `summary` = from existing Report row if already populated; otherwise empty list / empty string
   - `estimate` = `{"line_items": quote.line_items}`
   - `estimate_total` = quote.total
   - `vehicle` = full `session.vehicle` JSON snapshot
   - `status` = "final"
   - `title` = `"{year} {make} {model} — Inspection"` (built from `session.vehicle`)

5. **Backend** — generates PDFs via `PDFService` (`src/services/pdf.py`):
   - `generate_estimate(quote, session, shop) → bytes` using `reportlab`
   - `generate_report(report, media_urls, shop) → bytes` using `reportlab`
   - Media URLs: fetched from `media_files` where `session_id = session.id` and `s3_url` starts with `http` (skips local dev fallback URLs).

6. **Backend** — uploads both PDFs to S3 via existing `StorageService`:
   - Key: `quotes/{quote_id}/estimate.pdf` → `quotes.pdf_url`
   - Key: `reports/{report_id}/report.pdf` → `reports.pdf_url`

7. **Backend** — updates `quotes.status = "final"` and returns:
   ```json
   {
     "quote_id": "…",
     "status": "final",
     "pdf_url": "https://s3…/estimate.pdf",
     "report_id": "…",
     "report_pdf_url": "https://s3…/report.pdf",
     "share_token": "…"
   }
   ```

8. **iOS** — `QuoteDetailView` transitions to "Final" state:
   - Status badge: `FINAL ✓` (green)
   - "Finalize Quote" button replaced by two buttons:
     - **"Open Estimate PDF"** — opens S3 URL in iOS Share Sheet (supports AirPrint, Save to Files, email)
     - **"Share Report Link"** — copies `https://backend.railway.app/r/{share_token}` to clipboard

### `PDFService` — Estimate layout sections

1. Dark header band: shop name, address, phone / "ESTIMATE" + number + date
2. Three-column info row: Customer | Vehicle (year/make/model, VIN, mileage) | Service Info (technician, labor rate, valid-until)
3. Line items table: Description (with subtitle), Type badge (Labor/Part), Qty, Unit Price, Total
4. Totals block (right-aligned): Labor subtotal, Parts subtotal, Tax, **TOTAL**
5. Authorization box: paragraph + Signature line + Date line

### `PDFService` — Inspection Report layout sections

1. Dark header band: shop name / "INSPECTION REPORT" + number + date + technician
2. Vehicle banner (single row): year/make/model, mileage, owner name, VIN
3. AI Summary (amber left-border callout box)
4. Findings table: Component | Condition badge (Service Now red / Monitor orange / Good green) | Technician Notes
5. Photo grid: up to 9 photos, 3 per row, with captions from `media_files.tag`
6. Estimate summary table: service → total per line, grand total row
7. Footer: share link URL, page number

### `QuoteDetailView` — state machine

```
draft
  ├─ line_items present → show table + "Finalize Quote" button (orange)
  └─ line_items empty   → "No items yet" + Refresh button + "Finalize Quote" button

finalizing (in-flight)
  └─ spinner, button disabled, "Generating PDFs…" subtitle

final
  ├─ line items table (read-only)
  ├─ "FINAL ✓" status badge (green)
  ├─ "Open Estimate PDF" button (filled)
  └─ "Share Report Link" button (outline)
```

### Consumer tab path

After finalization, the report appears at:

**Customers tab → [customer name] → [vehicle] → Reports tab**

The iOS `ReportsTab` calls `GET /vehicles/{vehicleId}/reports` which queries `Report.vehicle_id`. This matches because step 4 above sets `report.vehicle_id` from the session snapshot. The report card shows: title, status `final`, estimate total, and created date.

---

## New Files

| File | Purpose |
|---|---|
| `ios/AutoShop/Upload/UploadManager.swift` | Singleton URLSession background upload manager |
| `ios/AutoShop/Upload/UploadItem.swift` | `UploadItem` struct + `UploadStatus` enum |
| `backend/src/services/pdf.py` | `PDFService` with `generate_estimate` and `generate_report` |

## Modified Files

| File | Change |
|---|---|
| `ios/AutoShop/RecordingView.swift` | Replace `capturedMedia` array with `UploadManager` observation |
| `ios/AutoShop/Views/Inspect/QuoteDetailView.swift` | Add Finalize button, Final state with PDF buttons |
| `ios/AutoShop/SessionAPI.swift` | Add `finalizeQuote(quoteId:) → FinalizeQuoteResponse` |
| `ios/AutoShop/Network/APIModels.swift` | Add `FinalizeQuoteResponse` model |
| `backend/src/api/quotes.py` | Extend `PUT /quotes/{id}/finalize` to generate PDFs and upsert Report |

## Out of Scope

- Android parity (separate task)
- PDF templates customisable per shop (future)
- Customer email/SMS delivery of PDFs (future — `sent_to` field exists but not wired)
- Persistent upload queue across app restarts (covered by URLSession background delegate re-attachment)
