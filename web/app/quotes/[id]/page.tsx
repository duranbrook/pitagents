'use client'

import { useState, useEffect, useCallback, Suspense } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { AppShell } from '@/components/AppShell'
import { getQuote, updateQuoteLineItems, finalizeQuote } from '@/lib/api'
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
          onChange={e => set({ type: e.target.value as 'labor' | 'part' })}
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
      const updated = await updateQuoteLineItems(id, items)
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
      const result = await finalizeQuote(id)
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

          {/* Final state: PDF link */}
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
