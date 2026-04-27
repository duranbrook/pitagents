# Unified Quote Flow — Web Parity Design

## Goal

Align the web and iOS inspection flows so both produce the same outcome: a finalized quote with editable line items plus an inspection report. Currently the web bypasses the quote entirely, calling `POST /sessions/{id}/generate-report` directly, which results in worse estimate quality (Qdrant returns $0 for unknown parts) and no editable line items.

## Problem Statement

| | Web (today) | iOS |
|---|---|---|
| Endpoint | `POST /sessions/{id}/generate-report` | `POST /quotes` → `PUT /quotes/{id}/finalize` |
| Estimate source | Qdrant lookup (often $0) | Claude LLM (realistic) |
| Editable line items? | No | Yes |
| Report created? | Yes | Yes |

Nothing in the code enforces which client uses which path. The two paths share the same `build_report` service internally, but the web skips quote creation so its reports have no associated quote and no editable estimate.

## Target State

Both clients follow the same three-step flow:

```
create session
    → upload media (audio + photos)
    → POST /quotes  {session_id, transcript}   ← generates Claude estimate
    → show editable quote page
        → edit line items (optional)
    → PUT /quotes/{id}/finalize                ← runs inspection pipeline, generates report
    → redirect to report
```

### Estimate source (future)
LLM-based line items are acceptable for now. The plan is to migrate estimate generation to a DB/Qdrant parts catalog lookup once the catalog has adequate coverage, because LLMs occasionally hallucinate prices.

## Architecture

### Backend — no changes required
All needed endpoints already exist:
- `POST /quotes` — creates quote, stores transcript on session, calls Claude for line items
- `GET /quotes/{id}` — read quote with line items
- `PATCH /quotes/{id}/line-items` — replace line items, recalculate total (draft only)
- `PUT /quotes/{id}/finalize` — marks quote final, runs `build_report`, overrides estimate with quote line items, returns report URLs

### Web changes — three files

#### 1. `web/lib/types.ts`
Add:
```ts
export interface QuoteLineItem {
  type: string          // "labor" | "part"
  description: string
  qty: number
  unit_price: number
  total: number
}

export interface Quote {
  quote_id: string
  status: string        // "draft" | "final"
  total: number
  line_items: QuoteLineItem[]
  session_id: string | null
  created_at: string | null
}

export interface FinalizeQuoteResponse {
  quote_id: string
  status: string
  total: number
  pdf_url: string | null
  report_id: string | null
  report_pdf_url: string | null
  share_token: string | null
}
```

#### 2. `web/lib/api.ts`
Add four functions (the existing `generateReport` stays for backward compat but is no longer called by the inspect page):
```ts
createQuote(sessionId: string, transcript: string): Promise<Quote>
getQuote(quoteId: string): Promise<Quote>
updateLineItems(quoteId: string, lineItems: QuoteLineItem[]): Promise<Quote>
finalizeQuote(quoteId: string): Promise<FinalizeQuoteResponse>
```

#### 3. `web/app/inspect/page.tsx`
Change `handleAnalyze`: after uploading all media, call `createQuote(session_id, transcript)` and `router.push('/quotes/' + quote_id)` instead of `generateReport`.

The transcript is already available as local state from the `/transcribe` call made for the preview panel.

#### 4. `web/app/quotes/[id]/page.tsx` — NEW
Quote detail page. Two modes: read and edit.

**Read mode:**
- Status badge (DRAFT / FINAL)
- Running total
- Line items table: description | type | qty | unit price | total
- "Edit" button (top-right, draft only) → enter edit mode
- "Finalize Quote" button (orange, bottom, draft only) → `PUT /quotes/{id}/finalize` → `router.push('/reports?id=...')`

**Edit mode:**
- Each row: description text input, type selector (Labor/Part), qty input, unit price input, computed total
- Running total updates live as inputs change
- "Add Labor" / "Add Part" buttons append blank rows
- × button on each row to delete
- "Save" → `PATCH /quotes/{id}/line-items` → return to read mode
- "Cancel" → discard changes, return to read mode

## Data Flow

```
/inspect                          /quotes/[id]                   /reports?id=...
   |                                   |                               |
   | createSession()                   |                               |
   | uploadMedia() ×N                  |                               |
   | createQuote(sid, transcript)      |                               |
   |──────────────────────────────────▶|                               |
   |                                   | getQuote() on load            |
   |                                   | user edits (optional)         |
   |                                   | updateLineItems() on Save     |
   |                                   | finalizeQuote() on Finalize   |
   |                                   |───────────────────────────────▶
```

## Error Handling

- Quote creation fails → show error in inspect page, do not navigate
- Line item save fails → show inline error, keep edit mode open
- Finalize fails → show error banner, leave page on `/quotes/{id}` so user can retry

## Out of Scope

- Migrating estimate generation to DB/Qdrant (future work)
- Deprecating `POST /sessions/{id}/generate-report` (keep for backward compat)
- Android changes (not part of this spec)
