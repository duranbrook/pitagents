# Unified Quote Flow — Web Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the web inspect flow create a quote with editable line items before finalizing, matching the iOS flow and producing realistic Claude-generated estimates instead of $0 Qdrant fallbacks.

**Architecture:** Four web-only changes — add Quote types, add four API functions, redirect inspect to `/quotes/{id}` after uploads, create a new quote detail page with inline editing and finalize. Backend is unchanged.

**Tech Stack:** Next.js 15 App Router, React, TypeScript, Tailwind CSS, `@tanstack/react-query` (for data loading), `next/navigation` (routing)

---

## File Map

| File | Change |
|---|---|
| `web/lib/types.ts` | Add `QuoteLineItem`, `Quote`, `FinalizeQuoteResponse` |
| `web/lib/api.ts` | Add `createQuote`, `getQuote`, `updateLineItems`, `finalizeQuote`; fix `uploadSessionMedia` tag |
| `web/app/inspect/page.tsx` | Replace `generateReport` call with `createQuote` + redirect to `/quotes/{id}` |
| `web/app/quotes/[id]/page.tsx` | New: editable quote page with read/edit modes and finalize |

---

## Task 1: Add Quote types

**Files:**
- Modify: `web/lib/types.ts`

- [ ] **Step 1: Add three interfaces to the bottom of `web/lib/types.ts`**

```ts
export interface QuoteLineItem {
  type: string        // "labor" | "part"
  description: string
  qty: number
  unit_price: number
  total: number
}

export interface Quote {
  quote_id: string
  status: string      // "draft" | "final"
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

- [ ] **Step 2: Verify TypeScript is happy**

```bash
cd web && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors related to types.ts

- [ ] **Step 3: Commit**

```bash
git add web/lib/types.ts
git commit -m "feat(web): add Quote, QuoteLineItem, FinalizeQuoteResponse types"
```

---

## Task 2: Add API functions

**Files:**
- Modify: `web/lib/api.ts`

**Context:** The existing `uploadSessionMedia` doesn't send a `tag` field, which the backend requires (`Literal["vin","odometer","tire","damage","general"]`). Fix this in the same task.

- [ ] **Step 1: Fix `uploadSessionMedia` to accept and forward `tag`**

Find the existing function (around line 192) and replace it:

```ts
export async function uploadSessionMedia(
  sessionId: string,
  file: File,
  mediaType: 'audio' | 'video' | 'photo',
  tag: 'vin' | 'odometer' | 'tire' | 'damage' | 'general' = 'general',
): Promise<{ media_id: string; s3_url: string }> {
  const form = new FormData()
  form.append('file', file)
  form.append('media_type', mediaType)
  form.append('tag', tag)
  const res = await api.post(`/sessions/${sessionId}/media`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}
```

- [ ] **Step 2: Add the four quote API functions at the bottom of `web/lib/api.ts`**

```ts
// ── Quotes ────────────────────────────────────────────────────────────────

import type { Quote, QuoteLineItem, FinalizeQuoteResponse } from './types'

export const createQuote = (
  sessionId: string,
  transcript: string,
): Promise<Quote> =>
  api.post('/quotes', { session_id: sessionId, transcript }).then(r => r.data)

export const getQuote = (quoteId: string): Promise<Quote> =>
  api.get(`/quotes/${quoteId}`).then(r => r.data)

export const updateLineItems = (
  quoteId: string,
  lineItems: QuoteLineItem[],
): Promise<Quote> =>
  api.patch(`/quotes/${quoteId}/line-items`, { line_items: lineItems }).then(r => r.data)

export const finalizeQuoteApi = (quoteId: string): Promise<FinalizeQuoteResponse> =>
  api.put(`/quotes/${quoteId}/finalize`, {}).then(r => r.data)
```

Note: the function is named `finalizeQuoteApi` to avoid a conflict with the local variable `finalizeQuote` that will exist in the quote page component.

- [ ] **Step 3: Verify TypeScript**

```bash
cd web && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add web/lib/api.ts
git commit -m "feat(web): add quote API functions and fix uploadSessionMedia tag"
```

---

## Task 3: Update inspect page to use the quote flow

**Files:**
- Modify: `web/app/inspect/page.tsx`

**Context:** `handleAnalyze` currently ends with `generateReport(session_id)` and redirects to `/reports?id=...`. Replace that last step with `createQuote(session_id, transcript)` and redirect to `/quotes/{id}`.

- [ ] **Step 1: Update the imports at the top of `web/app/inspect/page.tsx`**

Replace:
```ts
import {
  getCustomers,
  getVehicles,
  createSession,
  uploadSessionMedia,
  generateReport,
  transcribeAudio,
} from '@/lib/api'
```

With:
```ts
import {
  getCustomers,
  getVehicles,
  createSession,
  uploadSessionMedia,
  createQuote,
  transcribeAudio,
} from '@/lib/api'
```

- [ ] **Step 2: Replace the last part of `handleAnalyze`**

Find and replace the block starting at `const result = await generateReport(session_id)`:

Old:
```ts
      const result = await generateReport(session_id)
      router.push(`/reports?id=${result.report_id}`)
```

New:
```ts
      const quote = await createQuote(session_id, transcript)
      router.push(`/quotes/${quote.quote_id}`)
```

- [ ] **Step 3: Verify TypeScript**

```bash
cd web && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add web/app/inspect/page.tsx
git commit -m "feat(web): redirect inspect flow to editable quote instead of report"
```

---

## Task 4: Create the quote detail page

**Files:**
- Create: `web/app/quotes/[id]/page.tsx`

This page has two modes. **Read mode** shows the quote with a table of line items, an Edit button, and a Finalize button (draft only). **Edit mode** shows the same table with inline inputs, Add Labor/Part buttons, and Save/Cancel.

- [ ] **Step 1: Create the directory**

```bash
mkdir -p web/app/quotes/\[id\]
```

- [ ] **Step 2: Create `web/app/quotes/[id]/page.tsx` with this full content**

```tsx
'use client'

import { useState, useEffect, useCallback, Suspense } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { AppShell } from '@/components/AppShell'
import { getQuote, updateLineItems, finalizeQuoteApi } from '@/lib/api'
import type { Quote, QuoteLineItem } from '@/lib/types'

// ── Editable row ──────────────────────────────────────────────────────────

function EditRow({
  item,
  onChange,
  onDelete,
}: {
  item: QuoteLineItem & { _id: string }
  onChange: (updated: QuoteLineItem & { _id: string }) => void
  onDelete: () => void
}) {
  function set(patch: Partial<QuoteLineItem>) {
    const next = { ...item, ...patch }
    next.total = next.qty * next.unit_price
    onChange(next)
  }

  return (
    <tr className="border-t border-gray-800">
      <td className="px-3 py-2">
        <input
          value={item.description}
          onChange={e => set({ description: e.target.value })}
          placeholder="Description"
          className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500"
        />
      </td>
      <td className="px-3 py-2">
        <select
          value={item.type}
          onChange={e => set({ type: e.target.value })}
          className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-indigo-500"
        >
          <option value="labor">Labor</option>
          <option value="part">Part</option>
        </select>
      </td>
      <td className="px-3 py-2">
        <input
          type="number"
          min="0"
          step="0.5"
          value={item.qty}
          onChange={e => set({ qty: parseFloat(e.target.value) || 0 })}
          className="w-20 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white text-right focus:outline-none focus:border-indigo-500"
        />
      </td>
      <td className="px-3 py-2">
        <input
          type="number"
          min="0"
          step="0.01"
          value={item.unit_price}
          onChange={e => set({ unit_price: parseFloat(e.target.value) || 0 })}
          className="w-24 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white text-right focus:outline-none focus:border-indigo-500"
        />
      </td>
      <td className="px-3 py-2 text-right text-sm text-white font-semibold">
        ${(item.qty * item.unit_price).toFixed(2)}
      </td>
      <td className="px-3 py-2">
        <button
          onClick={onDelete}
          className="text-gray-600 hover:text-red-400 transition-colors text-lg leading-none"
          title="Remove row"
        >
          ×
        </button>
      </td>
    </tr>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────

function QuotePageInner() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()

  const [quote, setQuote] = useState<Quote | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [isEditing, setIsEditing] = useState(false)
  const [editItems, setEditItems] = useState<(QuoteLineItem & { _id: string })[]>([])
  const [saving, setSaving] = useState(false)
  const [finalizing, setFinalizing] = useState(false)

  const load = useCallback(async () => {
    try {
      const q = await getQuote(id)
      setQuote(q)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load quote')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { load() }, [load])

  function startEditing() {
    if (!quote) return
    setEditItems(quote.line_items.map(item => ({ ...item, _id: crypto.randomUUID() })))
    setIsEditing(true)
  }

  function cancelEditing() {
    setIsEditing(false)
    setEditItems([])
  }

  async function saveEdits() {
    setSaving(true)
    setError(null)
    try {
      const items: QuoteLineItem[] = editItems.map(({ _id, ...rest }) => ({
        ...rest,
        total: rest.qty * rest.unit_price,
      }))
      const updated = await updateLineItems(id, items)
      setQuote(updated)
      setIsEditing(false)
      setEditItems([])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  async function handleFinalize() {
    setFinalizing(true)
    setError(null)
    try {
      const result = await finalizeQuoteApi(id)
      if (result.report_id) {
        router.push(`/reports?id=${result.report_id}`)
      } else {
        await load()
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Finalize failed')
      setFinalizing(false)
    }
  }

  function addRow(type: 'labor' | 'part') {
    setEditItems(prev => [
      ...prev,
      { _id: crypto.randomUUID(), type, description: '', qty: 1, unit_price: 0, total: 0 },
    ])
  }

  const editTotal = editItems.reduce((sum, item) => sum + item.qty * item.unit_price, 0)

  if (loading) {
    return (
      <AppShell>
        <div className="flex h-full items-center justify-center text-gray-500 text-sm">
          Loading…
        </div>
      </AppShell>
    )
  }

  if (!quote) {
    return (
      <AppShell>
        <div className="flex h-full items-center justify-center text-gray-500 text-sm">
          Quote not found
        </div>
      </AppShell>
    )
  }

  const isDraft = quote.status === 'draft'
  const displayTotal = isEditing ? editTotal : quote.total

  return (
    <AppShell>
      <div className="h-full overflow-y-auto bg-gray-950">
        <div className="max-w-3xl mx-auto p-6 space-y-6">

          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-white">Quote</h1>
              <p className="text-xs text-gray-500 mt-0.5 font-mono">{quote.quote_id.slice(0, 8)}…</p>
            </div>
            <div className="flex items-center gap-3">
              <span
                className={`text-xs font-bold px-3 py-1 rounded-full ${
                  isDraft
                    ? 'bg-orange-900/40 text-orange-300 border border-orange-800'
                    : 'bg-green-900/40 text-green-300 border border-green-800'
                }`}
              >
                {isDraft ? 'DRAFT' : 'FINAL ✓'}
              </span>
              {isDraft && !isEditing && (
                <button
                  onClick={startEditing}
                  className="text-sm border border-gray-700 text-gray-300 px-3 py-1.5 rounded-lg hover:bg-gray-800 transition-colors"
                >
                  Edit
                </button>
              )}
              {isEditing && (
                <>
                  <button
                    onClick={cancelEditing}
                    className="text-sm border border-gray-700 text-gray-400 px-3 py-1.5 rounded-lg hover:bg-gray-800 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={saveEdits}
                    disabled={saving}
                    className="text-sm bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-3 py-1.5 rounded-lg transition-colors"
                  >
                    {saving ? 'Saving…' : 'Save'}
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Error banner */}
          {error && (
            <div className="bg-red-900/20 border border-red-800 text-red-300 text-sm px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          {/* Total */}
          <div className="flex items-baseline gap-3">
            <span className="text-gray-500 text-sm">Total</span>
            <span className="text-3xl font-bold text-white">${displayTotal.toFixed(2)}</span>
          </div>

          {/* Line items table */}
          <div className="border border-gray-700 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-800">
                <tr>
                  <th className="text-left text-xs text-gray-400 px-3 py-2.5 font-medium">Description</th>
                  <th className="text-left text-xs text-gray-400 px-3 py-2.5 font-medium">Type</th>
                  <th className="text-right text-xs text-gray-400 px-3 py-2.5 font-medium">Qty</th>
                  <th className="text-right text-xs text-gray-400 px-3 py-2.5 font-medium">Unit Price</th>
                  <th className="text-right text-xs text-gray-400 px-3 py-2.5 font-medium">Total</th>
                  {isEditing && <th className="w-8" />}
                </tr>
              </thead>
              <tbody>
                {isEditing ? (
                  editItems.map((item, i) => (
                    <EditRow
                      key={item._id}
                      item={item}
                      onChange={updated =>
                        setEditItems(prev => prev.map((x, j) => (j === i ? updated : x)))
                      }
                      onDelete={() => setEditItems(prev => prev.filter((_, j) => j !== i))}
                    />
                  ))
                ) : quote.line_items.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-6 text-center text-gray-600 text-sm">
                      No line items
                    </td>
                  </tr>
                ) : (
                  quote.line_items.map((item, i) => (
                    <tr key={i} className="border-t border-gray-800">
                      <td className="px-3 py-2.5 text-white">{item.description}</td>
                      <td className="px-3 py-2.5 text-gray-400 capitalize">{item.type}</td>
                      <td className="px-3 py-2.5 text-right text-gray-400">
                        {item.qty % 1 === 0 ? item.qty : item.qty.toFixed(1)}
                      </td>
                      <td className="px-3 py-2.5 text-right text-gray-400">
                        ${item.unit_price.toFixed(2)}
                      </td>
                      <td className="px-3 py-2.5 text-right text-white font-semibold">
                        ${item.total.toFixed(2)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
              {!isEditing && quote.line_items.length > 0 && (
                <tfoot className="bg-gray-800">
                  <tr>
                    <td colSpan={4} className="px-3 py-2.5 text-right text-sm font-semibold text-white">
                      Grand Total
                    </td>
                    <td className="px-3 py-2.5 text-right text-indigo-400 font-bold text-base">
                      ${quote.total.toFixed(2)}
                    </td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>

          {/* Add row buttons (edit mode only) */}
          {isEditing && (
            <div className="flex gap-3">
              <button
                onClick={() => addRow('labor')}
                className="text-sm border border-dashed border-gray-700 text-gray-400 px-4 py-2 rounded-lg hover:border-gray-500 hover:text-gray-200 transition-colors"
              >
                + Add Labor
              </button>
              <button
                onClick={() => addRow('part')}
                className="text-sm border border-dashed border-gray-700 text-gray-400 px-4 py-2 rounded-lg hover:border-gray-500 hover:text-gray-200 transition-colors"
              >
                + Add Part
              </button>
            </div>
          )}

          {/* Finalize button (draft, not editing) */}
          {isDraft && !isEditing && (
            <button
              onClick={handleFinalize}
              disabled={finalizing}
              className="w-full bg-orange-600 hover:bg-orange-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition-colors"
            >
              {finalizing ? '⏳ Generating report…' : '✓ Finalize Quote'}
            </button>
          )}

          {/* Final state: links */}
          {!isDraft && (
            <div className="flex gap-3">
              <a
                href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/quotes/${quote.quote_id}/pdf`}
                target="_blank"
                rel="noreferrer"
                className="text-sm bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-500 transition-colors"
              >
                🖨 Estimate PDF
              </a>
            </div>
          )}

        </div>
      </div>
    </AppShell>
  )
}

export default function QuotePage() {
  return (
    <Suspense>
      <QuotePageInner />
    </Suspense>
  )
}
```

- [ ] **Step 3: Verify TypeScript**

```bash
cd web && npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors

- [ ] **Step 4: Start the dev server and test the full flow**

```bash
cd web && npm run dev
```

Open `http://localhost:3000` in a browser. Then:
1. Log in with `owner@shop.com` / `testpass`
2. Navigate to Inspect
3. Select a customer and vehicle
4. Upload any audio file (can be a short .mp3)
5. Click "Analyze Inspection"
6. Verify the page redirects to `/quotes/{id}` and shows a draft quote with line items
7. Click "Edit" — verify all rows become editable inputs
8. Change a description, qty, or unit price — verify the total updates live
9. Click "+ Add Labor" — verify a blank row appears
10. Click × on a row — verify it removes
11. Click "Save" — verify the table returns to read mode with updated values
12. Click "Finalize Quote" — verify a spinner appears, then redirect to `/reports?id=...`

- [ ] **Step 5: Commit**

```bash
git add web/app/quotes
git commit -m "feat(web): quote detail page with editable line items and finalize"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Quote types added (`QuoteLineItem`, `Quote`, `FinalizeQuoteResponse`)
- ✅ Four API functions: `createQuote`, `getQuote`, `updateLineItems`, `finalizeQuoteApi`
- ✅ `uploadSessionMedia` tag fix included
- ✅ Inspect page redirects to `/quotes/{id}` after upload
- ✅ Quote page: read mode with table
- ✅ Quote page: edit mode with inline inputs, live total
- ✅ Add Labor / Add Part buttons
- ✅ Delete row (× button)
- ✅ Save → `PATCH /quotes/{id}/line-items`
- ✅ Cancel → discard edits
- ✅ Finalize → `PUT /quotes/{id}/finalize` → redirect to report
- ✅ Error banner on all failure paths
- ✅ Final state: estimate PDF link shown

**No placeholders** — every step has complete code.

**Type consistency** — `QuoteLineItem` uses `unit_price` (snake_case, matching API) throughout. `FinalizeQuoteResponse.report_id` used in `handleFinalize`. `getQuote` / `updateLineItems` / `finalizeQuoteApi` all defined before use.
